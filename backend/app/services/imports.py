"""Excel/CSV imports (DESIGN.md §9): upload -> validate in background -> preview -> commit.

Validation and commit share one parser per import type. Commit re-parses the
stored file and applies only valid rows, all in the request's single transaction.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal, set_tenant
from app.core.deps import Ctx, CurrentUser
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.models import (
    AcademicYear,
    GuardianRelation,
    Import,
    ImportStatus,
    ImportType,
    MarkStatus,
    RoleType,
    SchoolClass,
    Section,
    Subject,
    TeacherAssignment,
)
from app.schemas.setup import GuardianIn, StudentIn, TeacherIn
from app.services import audit, excel, people
from app.services.marks import (
    MarksScope,
    _check_writable,
    apply_entries,
    enrolled_students,
    load_scope,
    parse_mark_value,
)
from app.services.phone import InvalidPhone, normalize_phone
from app.services.storage import get_storage

PREVIEW_ROWS = 50
_TYPE_COLUMNS = {
    ImportType.STUDENTS: excel.STUDENT_COLUMNS,
    ImportType.TEACHERS: excel.TEACHER_COLUMNS,
    ImportType.MARKS: excel.MARKS_COLUMNS,
}


@dataclass
class Parsed:
    total: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)  # valid, normalised
    errors: list[dict[str, Any]] = field(default_factory=list)

    def error(self, row: int, column: str | None, message: str) -> None:
        self.errors.append({"row": row, "column": column, "message": message})


# ------------------------------------------------------------- helpers
def _section_lookup(ctx: Ctx) -> dict[tuple[str, str], uuid.UUID]:
    year_id = ctx.db.scalar(
        select(AcademicYear.id).where(AcademicYear.school_id == ctx.school_id, AcademicYear.is_current.is_(True))
    )
    if year_id is None:
        return {}
    rows = ctx.db.execute(
        select(Section.id, SchoolClass.name, Section.name)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .where(Section.school_id == ctx.school_id, Section.academic_year_id == year_id)
    ).all()
    return {(c.strip().lower(), s.strip().lower()): sid for sid, c, s in rows}


def _norm_class(v: str) -> str:
    v = v.strip().lower()
    for prefix in ("class ", "class", "grade "):
        if v.startswith(prefix):
            v = v[len(prefix) :]
    return v.strip()


def _section_key(text: str) -> tuple[str, str] | None:
    """'7-A' / '7 A' / 'Class 7-A' -> ('7', 'a')."""
    t = text.strip()
    for sep in ("-", " ", "/"):
        if sep in t:
            c, _, s = t.rpartition(sep)
            return _norm_class(c), s.strip().lower()
    return None


GENDERS = {
    "M": "MALE",
    "MALE": "MALE",
    "BOY": "MALE",
    "F": "FEMALE",
    "FEMALE": "FEMALE",
    "GIRL": "FEMALE",
    "O": "OTHER",
    "OTHER": "OTHER",
}


# --------------------------------------------------------- parsers
def parse_students(ctx: Ctx, rows: list[tuple[int, dict[str, Any]]]) -> Parsed:
    p = Parsed(total=len(rows))
    sections = _section_lookup(ctx)
    if not sections:
        p.error(1, None, "Set a current academic year with sections before importing students")
        return p
    seen: dict[str, int] = {}
    for n, r in rows:
        before = len(p.errors)
        adm = excel.as_text(r["admission_no"])
        name = excel.as_text(r["full_name"])
        if not adm:
            p.error(n, "admission_no", "admission_no is required")
        elif len(adm) > 30:
            p.error(n, "admission_no", "admission_no is too long")
        elif adm in seen:
            p.error(n, "admission_no", f"duplicate of row {seen[adm]}")
        else:
            seen[adm] = n
        if not name:
            p.error(n, "full_name", "full_name is required")
        cls, sec = excel.as_text(r["class"]), excel.as_text(r["section"])
        section_id = sections.get((_norm_class(cls or ""), (sec or "").lower())) if cls and sec else None
        if not cls or not sec:
            p.error(n, "class", "class and section are required")
        elif section_id is None:
            p.error(n, "section", f"section {cls}-{sec} does not exist in the current year")
        dob = None
        try:
            dob = excel.parse_date(r["date_of_birth"])
        except ValueError as exc:
            p.error(n, "date_of_birth", str(exc))
        gender = None
        if r["gender"] is not None:
            gender = GENDERS.get(str(r["gender"]).strip().upper())
            if gender is None:
                p.error(n, "gender", "gender must be M, F or O")
        guardians = []
        for rel in ("father", "mother", "guardian"):
            g_name, g_phone = excel.as_text(r[f"{rel}_name"]), r[f"{rel}_phone"]
            if g_phone is None and g_name is None:
                continue
            if g_phone is None:
                p.error(n, f"{rel}_phone", f"{rel}_phone is required when {rel}_name is given")
                continue
            try:
                phone = normalize_phone(g_phone)
            except InvalidPhone as exc:
                p.error(n, f"{rel}_phone", str(exc))
                continue
            guardians.append(
                {"relation": rel.upper(), "phone": phone, "full_name": g_name or f"Parent of {name or adm}"}
            )
        if len(p.errors) == before:
            p.rows.append(
                {
                    "row": n,
                    "admission_no": adm,
                    "full_name": name,
                    "section_id": str(section_id),
                    "class": cls,
                    "section": sec,
                    "roll_no": excel.as_text(r["roll_no"]),
                    "date_of_birth": dob.isoformat() if dob else None,
                    "gender": gender,
                    "guardians": guardians,
                }
            )
    return p


def _subject_lookup(ctx: Ctx) -> dict[str, uuid.UUID]:
    out: dict[str, uuid.UUID] = {}
    for s in ctx.db.scalars(select(Subject).where(Subject.school_id == ctx.school_id)):
        out[s.name.strip().lower()] = s.id
        if s.code:
            out[s.code.strip().lower()] = s.id
    return out


def parse_teachers(ctx: Ctx, rows: list[tuple[int, dict[str, Any]]]) -> Parsed:
    p = Parsed(total=len(rows))
    sections, subjects = _section_lookup(ctx), _subject_lookup(ctx)
    seen: dict[str, int] = {}
    for n, r in rows:
        before = len(p.errors)
        name = excel.as_text(r["full_name"])
        if not name:
            p.error(n, "full_name", "full_name is required")
        phone = None
        try:
            phone = normalize_phone(r["phone"])
            if phone in seen:
                p.error(n, "phone", f"duplicate of row {seen[phone]}")
            seen[phone] = n
        except InvalidPhone as exc:
            p.error(n, "phone", str(exc))
        assignments: list[dict[str, str]] = []
        for part in (excel.as_text(r["assignments"]) or "").split(";"):
            if not part.strip():
                continue
            sec_text, _, subj_text = part.partition(":")
            key = _section_key(sec_text)
            sid = sections.get(key) if key else None
            subj = subjects.get(subj_text.strip().lower())
            if sid is None:
                p.error(n, "assignments", f"unknown section '{sec_text.strip()}'")
            elif subj is None:
                p.error(n, "assignments", f"unknown subject '{subj_text.strip()}'")
            else:
                assignments.append({"section_id": str(sid), "subject_id": str(subj)})
        class_teacher_of = None
        ct = excel.as_text(r["class_teacher_of"])
        if ct:
            key = _section_key(ct)
            class_teacher_of = sections.get(key) if key else None
            if class_teacher_of is None:
                p.error(n, "class_teacher_of", f"unknown section '{ct}'")
        email = excel.as_text(r["email"])
        if email and "@" not in email:
            p.error(n, "email", "email is not valid")
        if len(p.errors) == before:
            p.rows.append(
                {
                    "row": n,
                    "full_name": name,
                    "phone": phone,
                    "employee_code": excel.as_text(r["employee_code"]),
                    "email": email,
                    "designation": excel.as_text(r["designation"]),
                    "assignments": assignments,
                    "class_teacher_of": str(class_teacher_of) if class_teacher_of else None,
                }
            )
    return p


def parse_marks(ctx: Ctx, scope: MarksScope, rows: list[tuple[int, dict[str, Any]]], meta: dict[str, str]) -> Parsed:
    p = Parsed(total=len(rows))
    if meta and (
        meta.get("exam_subject_id") != str(scope.exam_subject.id) or meta.get("section_id") != str(scope.section.id)
    ):
        p.error(1, None, "This file was downloaded for a different exam, subject or section")
        return p
    by_adm = {s.admission_no.strip().lower(): s for s, _ in enrolled_students(ctx, scope.section)}
    seen: dict[str, int] = {}
    for n, r in rows:
        adm = (excel.as_text(r["admission_no"]) or "").lower()
        student = by_adm.get(adm)
        if not adm:
            p.error(n, "admission_no", "admission_no is required")
            continue
        if student is None:
            p.error(n, "admission_no", f"student {adm.upper()} is not in this section")
            continue
        if adm in seen:
            p.error(n, "admission_no", f"duplicate of row {seen[adm]}")
            continue
        seen[adm] = n
        if r["marks"] is None:
            continue  # left blank: not entered yet
        try:
            status, value = parse_mark_value(r["marks"], scope.exam_subject.max_marks)
        except ValueError as exc:
            p.error(n, "marks", f"Row {n}: {exc}")
            continue
        p.rows.append(
            {
                "row": n,
                "student_id": str(student.id),
                "student_name": student.full_name,
                "admission_no": student.admission_no,
                "status": status.value,
                "marks": str(value) if value is not None else None,
            }
        )
    return p


# ---------------------------------------------------------- lifecycle
def _check_type_permission(ctx: Ctx, import_type: ImportType) -> None:
    if import_type == ImportType.MARKS:
        if ctx.user.role not in (RoleType.TEACHER, RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL):
            raise Forbidden()
    elif ctx.user.role != RoleType.SCHOOL_ADMIN:
        raise Forbidden()


def create_import(
    ctx: Ctx,
    import_type: ImportType,
    filename: str,
    content: bytes,
    exam_subject_id: uuid.UUID | None,
    section_id: uuid.UUID | None,
) -> Import:
    _check_type_permission(ctx, import_type)
    s = get_settings()
    if len(content) > s.max_upload_mb * 1024 * 1024:
        raise ValidationFailed(f"File is larger than {s.max_upload_mb} MB", code="FILE_TOO_LARGE")
    lower = filename.lower()
    if not (lower.endswith(".xlsx") or lower.endswith(".csv")):
        raise ValidationFailed("Upload an .xlsx or .csv file", code="FILE_TYPE")
    if lower.endswith(".xlsx") and not content.startswith(b"PK"):
        raise ValidationFailed("File is not a valid .xlsx workbook", code="FILE_TYPE")
    context: dict[str, Any] = {"filename": filename[-120:]}
    if import_type == ImportType.MARKS:
        if exam_subject_id is None or section_id is None:
            raise ValidationFailed("exam_subject_id and section_id are required for marks imports")
        load_scope(ctx, exam_subject_id, section_id)  # permission check now, not just in background
        context.update(exam_subject_id=str(exam_subject_id), section_id=str(section_id))
    import_id = uuid.uuid4()
    ext = ".csv" if lower.endswith(".csv") else ".xlsx"
    key = f"imports/{ctx.school_id}/{import_id}{ext}"
    get_storage().put(key, content, "text/csv" if ext == ".csv" else excel.XLSX_MIME)
    imp = Import(
        id=import_id,
        school_id=ctx.school_id,
        type=import_type,
        status=ImportStatus.UPLOADED,
        file_key=key,
        context=context,
        created_by=ctx.user.user_id,
    )
    ctx.db.add(imp)
    ctx.db.flush()
    return imp


def _parse(ctx: Ctx, imp: Import) -> tuple[Parsed, MarksScope | None]:
    content = get_storage().get(imp.file_key)
    if content is None:
        raise NotFound("Uploaded file")
    rows, meta = excel.read_rows(content, imp.file_key, _TYPE_COLUMNS[imp.type], get_settings().max_import_rows)
    if imp.type == ImportType.STUDENTS:
        return parse_students(ctx, rows), None
    if imp.type == ImportType.TEACHERS:
        return parse_teachers(ctx, rows), None
    scope = load_scope(ctx, uuid.UUID(imp.context["exam_subject_id"]), uuid.UUID(imp.context["section_id"]))
    return parse_marks(ctx, scope, rows, meta), scope


def validate(ctx: Ctx, imp: Import) -> None:
    imp.status = ImportStatus.VALIDATING
    ctx.db.flush()
    try:
        parsed, _ = _parse(ctx, imp)
    except excel.SheetError as exc:
        imp.status, imp.errors, imp.total_rows, imp.valid_rows = (
            ImportStatus.FAILED,
            [{"row": None, "column": None, "message": str(exc)}],
            0,
            0,
        )
        return
    imp.total_rows, imp.valid_rows = parsed.total, len(parsed.rows)
    imp.errors = parsed.errors
    imp.context = {**imp.context, "preview": parsed.rows[:PREVIEW_ROWS]}
    imp.status = ImportStatus.READY


def validate_in_background(import_id: uuid.UUID, user: CurrentUser) -> None:
    """Background job: its own tenant-scoped session (the request's has closed)."""
    db = SessionLocal()
    set_tenant(db, user.school_id)
    try:
        ctx = Ctx(db=db, user=user)
        imp = db.scalar(select(Import).where(Import.id == import_id, Import.school_id == user.school_id))
        if imp is not None and imp.status == ImportStatus.UPLOADED:
            try:
                validate(ctx, imp)
            except Exception:
                db.rollback()
                imp = db.get(Import, import_id)
                if imp is not None:
                    imp.status = ImportStatus.FAILED
                    imp.errors = [{"row": None, "column": None, "message": "Could not read the file"}]
        db.commit()
    finally:
        db.close()


def get_import(ctx: Ctx, import_id: uuid.UUID) -> Import:
    imp = ctx.db.scalar(select(Import).where(Import.id == import_id, Import.school_id == ctx.school_id))
    if imp is None:
        raise NotFound("Import")
    if ctx.user.role == RoleType.TEACHER and imp.created_by != ctx.user.user_id:
        raise NotFound("Import")
    _check_type_permission(ctx, imp.type)
    return imp


def list_imports(ctx: Ctx, limit: int = 20) -> list[Import]:
    stmt = select(Import).where(Import.school_id == ctx.school_id).order_by(Import.created_at.desc()).limit(limit)
    if ctx.user.role == RoleType.TEACHER:
        stmt = stmt.where(Import.created_by == ctx.user.user_id)
    return list(ctx.db.scalars(stmt))


def commit(ctx: Ctx, import_id: uuid.UUID, reason: str | None = None) -> Import:
    imp = get_import(ctx, import_id)
    if imp.status == ImportStatus.COMMITTED:
        raise Conflict("This import was already saved", code="IMPORT_COMMITTED")
    if imp.status != ImportStatus.READY:
        raise Conflict("This import is not ready to save", code="IMPORT_NOT_READY")
    parsed, scope = _parse(ctx, imp)
    if not parsed.rows:
        raise ValidationFailed("There are no valid rows to save", code="IMPORT_EMPTY")
    imp.status = ImportStatus.COMMITTING
    summary: dict[str, int]
    if imp.type == ImportType.STUDENTS:
        summary = _commit_students(ctx, parsed)
    elif imp.type == ImportType.TEACHERS:
        summary = _commit_teachers(ctx, parsed)
    else:
        assert scope is not None
        _check_writable(ctx, scope, reason)
        valid = [
            (
                uuid.UUID(r["student_id"]),
                MarkStatus(r["status"]),
                Decimal(r["marks"]) if r["marks"] is not None else None,
            )
            for r in parsed.rows
        ]
        result = apply_entries(ctx, scope, valid, reason, source="import")
        summary = result.model_dump()
    imp.status = ImportStatus.COMMITTED
    imp.committed_at = datetime.now(UTC)
    imp.valid_rows = len(parsed.rows)
    imp.errors = parsed.errors
    imp.context = {**imp.context, "result": summary}
    audit.record(
        ctx,
        audit.Action.IMPORT_COMMIT,
        entity="import",
        entity_id=imp.id,
        new={"type": imp.type.value, "rows": len(parsed.rows), **summary},
        reason=reason,
    )
    ctx.db.flush()
    return imp


def _commit_students(ctx: Ctx, parsed: Parsed) -> dict[str, int]:
    created = updated = guardians = 0
    for r in parsed.rows:
        try:
            data = StudentIn(
                admission_no=r["admission_no"],
                full_name=r["full_name"],
                date_of_birth=r["date_of_birth"],
                gender=r["gender"],
                section_id=uuid.UUID(r["section_id"]),
                roll_no=r["roll_no"],
            )
        except ValidationError as exc:
            raise ValidationFailed(f"Row {r['row']}: {exc.errors()[0]['msg']}") from exc
        student, was_created = people.upsert_student(ctx, data)
        created += was_created
        updated += not was_created
        for i, g in enumerate(r["guardians"]):
            guardian, _ = people.upsert_guardian(ctx, GuardianIn(full_name=g["full_name"], phone=g["phone"]))
            people.link_guardian_ids(ctx, student.id, guardian.id, GuardianRelation(g["relation"]), i == 0)
            guardians += 1
    return {"created": created, "updated": updated, "guardian_links": guardians}


def _commit_teachers(ctx: Ctx, parsed: Parsed) -> dict[str, int]:
    created = updated = assigned = 0
    for r in parsed.rows:
        teacher, was_created = people.upsert_teacher(
            ctx,
            TeacherIn(
                full_name=r["full_name"],
                phone=r["phone"],
                employee_code=r["employee_code"],
                email=r["email"],
                designation=r["designation"],
            ),
        )
        created += was_created
        updated += not was_created
        for a in r["assignments"]:
            sec_id, subj_id = uuid.UUID(a["section_id"]), uuid.UUID(a["subject_id"])
            exists = ctx.db.scalar(
                select(TeacherAssignment.id).where(
                    TeacherAssignment.teacher_id == teacher.id,
                    TeacherAssignment.section_id == sec_id,
                    TeacherAssignment.subject_id == subj_id,
                )
            )
            if not exists:
                ctx.db.add(
                    TeacherAssignment(
                        school_id=ctx.school_id, teacher_id=teacher.id, section_id=sec_id, subject_id=subj_id
                    )
                )
                assigned += 1
        if r["class_teacher_of"]:
            section = ctx.db.scalar(
                select(Section).where(
                    Section.id == uuid.UUID(r["class_teacher_of"]), Section.school_id == ctx.school_id
                )
            )
            if section is not None:
                section.class_teacher_id = teacher.id
        ctx.db.flush()
    return {"created": created, "updated": updated, "assignments_added": assigned}


# ---------------------------------------------------------- templates
def marks_template(ctx: Ctx, exam_subject_id: uuid.UUID, section_id: uuid.UUID) -> tuple[bytes, str]:
    scope = load_scope(ctx, exam_subject_id, section_id)
    students = [(s.admission_no, e.roll_no, s.full_name) for s, e in enrolled_students(ctx, scope.section)]
    title = f"{scope.exam.name} · {scope.subject_name} · {scope.section_name}"
    data = excel.marks_template(
        exam_subject_id=scope.exam_subject.id,
        section_id=scope.section.id,
        title=title,
        max_marks=scope.exam_subject.max_marks,
        students=students,
    )
    safe = "".join(ch if ch.isalnum() else "_" for ch in f"marks_{scope.section_name}_{scope.subject_name}")
    return data, f"{safe}.xlsx"
