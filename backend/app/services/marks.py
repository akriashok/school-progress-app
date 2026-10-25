"""Marks entry, submission and result publication (DESIGN.md §5, §8)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, func, select

from app.core.deps import Ctx
from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.models import (
    AcademicYear,
    Exam,
    ExamSubject,
    Mark,
    MarksSubmission,
    MarkStatus,
    ResultPublication,
    RoleType,
    School,
    SchoolClass,
    Section,
    Student,
    StudentEnrolment,
    Subject,
    SubmissionStatus,
    TeacherAssignment,
)
from app.schemas.exams import (
    BulkMarksIn,
    BulkMarksOut,
    MarkEntry,
    MarkRow,
    MarksGrid,
    MyAssignment,
    PublicationOut,
    SubmissionOut,
)
from app.services import audit
from app.services.academics import get_owned, section_label
from app.services.grading import pass_marks_for
from app.services.permissions import teacher_can_access


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class MarksScope:
    exam: Exam
    exam_subject: ExamSubject
    section: Section
    section_name: str
    subject_name: str
    published: bool


def is_published(ctx: Ctx, exam_id: uuid.UUID, section_id: uuid.UUID) -> bool:
    return bool(
        ctx.db.scalar(
            select(func.count())
            .select_from(ResultPublication)
            .where(
                ResultPublication.school_id == ctx.school_id,
                ResultPublication.exam_id == exam_id,
                ResultPublication.section_id == section_id,
            )
        )
    )


def load_scope(ctx: Ctx, exam_subject_id: uuid.UUID, section_id: uuid.UUID) -> MarksScope:
    """Resolve and permission-check an (exam subject, section) pair."""
    es = get_owned(ctx, ExamSubject, exam_subject_id, "Exam subject")
    section = get_owned(ctx, Section, section_id, "Section")
    exam = get_owned(ctx, Exam, es.exam_id, "Exam")
    if es.class_id != section.class_id or exam.academic_year_id != section.academic_year_id:
        raise ValidationFailed("This exam subject is not for this section's class and year", code="SCOPE_MISMATCH")
    if ctx.user.role == RoleType.TEACHER:
        if not teacher_can_access(ctx, section.id, es.subject_id):
            raise Forbidden("You are not assigned to this section and subject")
    elif not ctx.user.is_school_manager:
        raise Forbidden()
    cls_name = ctx.db.scalar(select(SchoolClass.name).where(SchoolClass.id == section.class_id)) or ""
    subject_name = ctx.db.scalar(select(Subject.name).where(Subject.id == es.subject_id)) or ""
    return MarksScope(
        exam=exam,
        exam_subject=es,
        section=section,
        section_name=section_label(cls_name, section.name),
        subject_name=subject_name,
        published=is_published(ctx, exam.id, section.id),
    )


def enrolled_students(ctx: Ctx, section: Section) -> list[tuple[Student, StudentEnrolment]]:
    rows = ctx.db.execute(
        select(Student, StudentEnrolment)
        .join(StudentEnrolment, StudentEnrolment.student_id == Student.id)
        .where(
            StudentEnrolment.section_id == section.id,
            StudentEnrolment.school_id == ctx.school_id,
            StudentEnrolment.academic_year_id == section.academic_year_id,
            Student.deleted_at.is_(None),
        )
    ).all()
    out = [(s, e) for s, e in rows]
    out.sort(key=lambda r: (_roll_key(r[1].roll_no), r[0].full_name))
    return out


def _roll_key(roll: str | None) -> tuple[int, int, str]:
    if roll is None:
        return (1, 0, "")
    return (0, int(roll), "") if roll.isdigit() else (0, 10**6, roll)


def _pass_marks(ctx: Ctx, es: ExamSubject) -> Decimal:
    pp = ctx.db.scalar(select(School.pass_percent).where(School.id == ctx.school_id)) or Decimal(33)
    return pass_marks_for(es.max_marks, es.pass_marks, pp).quantize(Decimal("0.01"))


def _submission(ctx: Ctx, scope: MarksScope) -> MarksSubmission | None:
    return ctx.db.scalar(
        select(MarksSubmission).where(
            MarksSubmission.exam_subject_id == scope.exam_subject.id,
            MarksSubmission.section_id == scope.section.id,
            MarksSubmission.school_id == ctx.school_id,
        )
    )


def get_grid(ctx: Ctx, exam_subject_id: uuid.UUID, section_id: uuid.UUID) -> MarksGrid:
    scope = load_scope(ctx, exam_subject_id, section_id)
    marks = {
        m.student_id: m
        for m in ctx.db.scalars(
            select(Mark).where(Mark.exam_subject_id == scope.exam_subject.id, Mark.school_id == ctx.school_id)
        )
    }
    rows = []
    for s, e in enrolled_students(ctx, scope.section):
        m = marks.get(s.id)
        rows.append(
            MarkRow(
                student_id=s.id,
                admission_no=s.admission_no,
                roll_no=e.roll_no,
                full_name=s.full_name,
                status=m.status if m else None,
                marks=m.marks_obtained if m else None,
                version=m.version if m else None,
            )
        )
    sub = _submission(ctx, scope)
    teacher = ctx.user.role == RoleType.TEACHER
    return MarksGrid(
        exam_id=scope.exam.id,
        exam_name=scope.exam.name,
        exam_subject_id=scope.exam_subject.id,
        subject_name=scope.subject_name,
        section_id=scope.section.id,
        section_name=scope.section_name,
        max_marks=scope.exam_subject.max_marks,
        pass_marks=_pass_marks(ctx, scope.exam_subject),
        submission_status=sub.status if sub else None,
        submitted_at=sub.submitted_at if sub else None,
        published=scope.published,
        can_edit=not (teacher and scope.published),
        reason_required=scope.published and not teacher,
        rows=rows,
    )


# ---------------------------------------------------------- validation
def parse_mark_value(raw: Any, max_marks: Decimal) -> tuple[MarkStatus, Decimal | None]:
    """Parse a grid/Excel value: number, 'AB' (absent) or 'EX' (exempted)."""
    if isinstance(raw, str):
        token = raw.strip().upper()
        if token in ("AB", "A", "ABSENT"):
            return MarkStatus.ABSENT, None
        if token in ("EX", "EXEMPT", "EXEMPTED"):
            return MarkStatus.EXEMPT, None
        if token == "":
            raise ValueError("marks are empty")
        raw = token
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"'{raw}' is not a number, AB or EX") from exc
    return MarkStatus.PRESENT, check_marks(value, max_marks)


def check_marks(value: Decimal, max_marks: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("marks must be a number")
    if value < 0:
        raise ValueError("marks cannot be negative")
    if value > max_marks:
        raise ValueError(f"marks {value.normalize():f} > max {max_marks.normalize():f}")
    if value != value.quantize(Decimal("0.01")):
        raise ValueError("marks can have at most 2 decimals")
    return value.quantize(Decimal("0.01"))


def validate_entries(
    ctx: Ctx, scope: MarksScope, entries: list[MarkEntry]
) -> tuple[list[tuple[uuid.UUID, MarkStatus, Decimal | None]], list[dict[str, Any]]]:
    enrolled = {s.id for s, _ in enrolled_students(ctx, scope.section)}
    seen: set[uuid.UUID] = set()
    valid: list[tuple[uuid.UUID, MarkStatus, Decimal | None]] = []
    errors: list[dict[str, Any]] = []
    for i, e in enumerate(entries):

        def err(msg: str, e: MarkEntry = e, i: int = i) -> None:
            errors.append({"index": i, "student_id": str(e.student_id), "message": msg})

        if e.student_id not in enrolled:
            err("student is not in this section")
            continue
        if e.student_id in seen:
            err("student appears more than once")
            continue
        seen.add(e.student_id)
        if e.status == MarkStatus.PRESENT:
            if e.marks is None:
                continue  # blank cell: nothing to save
            try:
                valid.append((e.student_id, e.status, check_marks(e.marks, scope.exam_subject.max_marks)))
            except ValueError as exc:
                err(str(exc))
        else:
            valid.append((e.student_id, e.status, None))
    return valid, errors


def _check_writable(ctx: Ctx, scope: MarksScope, reason: str | None) -> None:
    if scope.published:
        if ctx.user.role == RoleType.TEACHER:
            raise Forbidden("Results are published; ask the principal to unpublish to edit", code="RESULTS_PUBLISHED")
        if not reason or not reason.strip():
            raise ValidationFailed("A reason is required to change published marks", code="REASON_REQUIRED")


def apply_entries(
    ctx: Ctx,
    scope: MarksScope,
    valid: list[tuple[uuid.UUID, MarkStatus, Decimal | None]],
    reason: str | None,
    source: str = "grid",
) -> BulkMarksOut:
    existing = {
        m.student_id: m
        for m in ctx.db.scalars(
            select(Mark)
            .where(
                Mark.exam_subject_id == scope.exam_subject.id,
                Mark.school_id == ctx.school_id,
                Mark.student_id.in_([v[0] for v in valid]),
            )
            .with_for_update()
        )
    }
    created = updated = unchanged = 0
    for student_id, status, value in valid:
        m = existing.get(student_id)
        new = {"status": status.value, "marks": str(value) if value is not None else None}
        if m is None:
            m = Mark(
                school_id=ctx.school_id,
                exam_subject_id=scope.exam_subject.id,
                student_id=student_id,
                section_id=scope.section.id,
                status=status,
                marks_obtained=value,
                entered_by=ctx.user.user_id,
                version=1,
            )
            ctx.db.add(m)
            ctx.db.flush()
            audit.record(
                ctx,
                audit.Action.MARK_CREATE,
                entity="mark",
                entity_id=m.id,
                new={**new, "source": source},
                reason=reason,
            )
            created += 1
        elif m.status == status and m.marks_obtained == value:
            unchanged += 1
        else:
            old = {
                "status": m.status.value,
                "marks": str(m.marks_obtained) if m.marks_obtained is not None else None,
                "version": m.version,
            }
            m.status, m.marks_obtained = status, value
            m.entered_by = ctx.user.user_id
            m.section_id = scope.section.id
            m.version += 1
            audit.record(
                ctx,
                audit.Action.MARK_UPDATE,
                entity="mark",
                entity_id=m.id,
                old=old,
                new={**new, "version": m.version, "source": source},
                reason=reason,
            )
            updated += 1
    if _submission(ctx, scope) is None:
        ctx.db.add(
            MarksSubmission(
                school_id=ctx.school_id,
                exam_subject_id=scope.exam_subject.id,
                section_id=scope.section.id,
                status=SubmissionStatus.DRAFT,
            )
        )
    ctx.db.flush()
    return BulkMarksOut(created=created, updated=updated, unchanged=unchanged)


def bulk_put(ctx: Ctx, data: BulkMarksIn) -> BulkMarksOut:
    scope = load_scope(ctx, data.exam_subject_id, data.section_id)
    _check_writable(ctx, scope, data.reason)
    valid, errors = validate_entries(ctx, scope, data.entries)
    if errors:
        raise ValidationFailed("Some marks are not valid", code="MARKS_INVALID", details=errors)
    return apply_entries(ctx, scope, valid, data.reason)


def submit(ctx: Ctx, exam_subject_id: uuid.UUID, section_id: uuid.UUID) -> SubmissionOut:
    scope = load_scope(ctx, exam_subject_id, section_id)
    if scope.published:
        raise Forbidden("Results are already published", code="RESULTS_PUBLISHED")
    students = {s.id for s, _ in enrolled_students(ctx, scope.section)}
    entered = set(
        ctx.db.scalars(
            select(Mark.student_id).where(
                Mark.exam_subject_id == scope.exam_subject.id, Mark.school_id == ctx.school_id
            )
        )
    )
    missing = students - entered
    if missing:
        raise ValidationFailed(
            f"Marks are missing for {len(missing)} student(s)",
            code="MARKS_INCOMPLETE",
            details={"missing_student_ids": sorted(str(m) for m in missing)},
        )
    sub = _submission(ctx, scope)
    if sub is None:
        sub = MarksSubmission(
            school_id=ctx.school_id, exam_subject_id=scope.exam_subject.id, section_id=scope.section.id
        )
        ctx.db.add(sub)
    sub.status, sub.submitted_by, sub.submitted_at = SubmissionStatus.SUBMITTED, ctx.user.user_id, _now()
    ctx.db.flush()
    audit.record(ctx, audit.Action.MARKS_SUBMIT, entity="marks_submission", entity_id=sub.id)
    return SubmissionOut(
        exam_subject_id=scope.exam_subject.id,
        section_id=scope.section.id,
        status=sub.status,
        submitted_at=sub.submitted_at,
    )


# ------------------------------------------------------- teacher home
def my_assignments(ctx: Ctx, academic_year_id: uuid.UUID | None = None) -> list[MyAssignment]:
    if ctx.user.teacher_id is None:
        raise Forbidden()
    year_id = academic_year_id or ctx.db.scalar(
        select(AcademicYear.id).where(AcademicYear.school_id == ctx.school_id, AcademicYear.is_current.is_(True))
    )
    counts = (
        select(StudentEnrolment.section_id, func.count().label("n"))
        .where(StudentEnrolment.school_id == ctx.school_id)
        .group_by(StudentEnrolment.section_id)
        .subquery()
    )
    stmt = (
        select(Section, SchoolClass, Subject, func.coalesce(counts.c.n, 0))
        .join(TeacherAssignment, TeacherAssignment.section_id == Section.id)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .join(Subject, Subject.id == TeacherAssignment.subject_id)
        .outerjoin(counts, counts.c.section_id == Section.id)
        .where(TeacherAssignment.school_id == ctx.school_id, TeacherAssignment.teacher_id == ctx.user.teacher_id)
        .order_by(SchoolClass.sort_order, Section.name, Subject.name)
    )
    if year_id:
        stmt = stmt.where(Section.academic_year_id == year_id)
    return [
        MyAssignment(
            section_id=sec.id,
            section_name=section_label(cls.name, sec.name),
            class_id=cls.id,
            subject_id=subj.id,
            subject_name=subj.name,
            academic_year_id=sec.academic_year_id,
            student_count=int(n),
            is_class_teacher=sec.class_teacher_id == ctx.user.teacher_id,
        )
        for sec, cls, subj, n in ctx.db.execute(stmt).all()
    ]


# --------------------------------------------------------- publishing
def _exam_sections(ctx: Ctx, exam: Exam, section_ids: list[uuid.UUID] | None) -> list[Section]:
    stmt = select(Section).where(Section.school_id == ctx.school_id, Section.academic_year_id == exam.academic_year_id)
    if section_ids is not None:
        stmt = stmt.where(Section.id.in_(section_ids))
    sections = list(ctx.db.scalars(stmt))
    if section_ids is not None and len(sections) != len(set(section_ids)):
        raise NotFound("Section")
    return sections


def list_publications(ctx: Ctx, exam_id: uuid.UUID) -> list[PublicationOut]:
    get_owned(ctx, Exam, exam_id, "Exam")
    rows = ctx.db.execute(
        select(ResultPublication, Section, SchoolClass)
        .join(Section, Section.id == ResultPublication.section_id)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .where(ResultPublication.exam_id == exam_id, ResultPublication.school_id == ctx.school_id)
        .order_by(SchoolClass.sort_order, Section.name)
    ).all()
    return [
        PublicationOut(section_id=s.id, section_name=section_label(c.name, s.name), published_at=p.published_at)
        for p, s, c in rows
    ]


def publish(ctx: Ctx, exam_id: uuid.UUID, section_ids: list[uuid.UUID] | None) -> list[uuid.UUID]:
    """Publish results; returns the sections that were newly published."""
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    already = set(
        ctx.db.scalars(
            select(ResultPublication.section_id).where(
                ResultPublication.exam_id == exam.id, ResultPublication.school_id == ctx.school_id
            )
        )
    )
    newly: list[uuid.UUID] = []
    for section in _exam_sections(ctx, exam, section_ids):
        if section.id in already:
            continue
        pub = ResultPublication(
            school_id=ctx.school_id, exam_id=exam.id, section_id=section.id, published_by=ctx.user.user_id
        )
        ctx.db.add(pub)
        ctx.db.flush()
        audit.record(
            ctx,
            audit.Action.RESULT_PUBLISH,
            entity="result_publication",
            entity_id=pub.id,
            new={"exam_id": exam.id, "section_id": section.id},
        )
        newly.append(section.id)
    return newly


def unpublish(ctx: Ctx, exam_id: uuid.UUID, section_ids: list[uuid.UUID] | None) -> int:
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    pubs = list(
        ctx.db.scalars(
            select(ResultPublication).where(
                ResultPublication.exam_id == exam.id,
                ResultPublication.school_id == ctx.school_id,
                *([ResultPublication.section_id.in_(section_ids)] if section_ids is not None else []),
            )
        )
    )
    for p in pubs:
        audit.record(
            ctx,
            audit.Action.RESULT_UNPUBLISH,
            entity="result_publication",
            entity_id=p.id,
            old={"exam_id": exam.id, "section_id": p.section_id},
        )
    if pubs:
        ctx.db.execute(delete(ResultPublication).where(ResultPublication.id.in_([p.id for p in pubs])))
        ctx.db.flush()
    return len(pubs)
