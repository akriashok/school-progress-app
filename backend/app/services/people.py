"""People: teachers, teacher assignments, students (+ enrolments, PINs), guardians."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.orm import aliased

from app.core.deps import Ctx
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import hash_pin
from app.models import (
    Guardian,
    RoleType,
    SchoolClass,
    Section,
    Student,
    StudentEnrolment,
    StudentGuardian,
    Subject,
    Teacher,
    TeacherAssignment,
)
from app.schemas.common import Page, PageParams
from app.schemas.setup import (
    AssignmentIn,
    AssignmentOut,
    GuardianIn,
    GuardianLinkIn,
    GuardianOut,
    GuardianUpdate,
    StudentDetail,
    StudentGuardianOut,
    StudentIn,
    StudentOut,
    StudentUpdate,
    TeacherIn,
    TeacherOut,
    TeacherUpdate,
)
from app.services import audit
from app.services.academics import flush_or_conflict, get_owned, section_label
from app.services.users import deactivate_roles, ensure_role, get_or_create_user


def _now() -> datetime:
    return datetime.now(UTC)


def _paginate(ctx: Ctx, stmt: Select[Any], params: PageParams) -> tuple[list[Any], int]:
    total = ctx.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = ctx.db.execute(stmt.limit(params.page_size).offset(params.offset)).all()
    return list(rows), int(total)


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"


# --------------------------------------------------------------- teachers
def list_teachers(ctx: Ctx, params: PageParams, q: str | None = None) -> Page[TeacherOut]:
    stmt = select(Teacher).where(Teacher.school_id == ctx.school_id, Teacher.deleted_at.is_(None))
    if q:
        stmt = stmt.where(
            or_(Teacher.full_name.ilike(_like(q)), Teacher.phone.ilike(_like(q)), Teacher.employee_code.ilike(_like(q)))
        )
    rows, total = _paginate(ctx, stmt.order_by(Teacher.full_name), params)
    return Page(
        items=[TeacherOut.model_validate(r[0]) for r in rows], total=total, page=params.page, page_size=params.page_size
    )


def get_teacher(ctx: Ctx, teacher_id: uuid.UUID) -> Teacher:
    t = get_owned(ctx, Teacher, teacher_id, "Teacher")
    if t.deleted_at is not None:
        raise NotFound("Teacher")
    return t


def upsert_teacher(ctx: Ctx, data: TeacherIn) -> tuple[Teacher, bool]:
    """Create or update by natural key (school, phone). Returns (teacher, created)."""
    db = ctx.db
    t = db.scalar(select(Teacher).where(Teacher.school_id == ctx.school_id, Teacher.phone == data.phone))
    created = t is None
    if t is None:
        t = Teacher(school_id=ctx.school_id, **data.model_dump())
        db.add(t)
    else:
        for k, v in data.model_dump().items():
            setattr(t, k, v)
        t.deleted_at = None
    db.flush()
    user = get_or_create_user(db, data.phone, data.full_name)
    t.user_id = user.id
    ensure_role(db, user.id, RoleType.TEACHER, ctx.school_id, teacher_id=t.id)
    return t, created


def create_teacher(ctx: Ctx, data: TeacherIn) -> Teacher:
    existing = ctx.db.scalar(
        select(Teacher).where(
            Teacher.school_id == ctx.school_id, Teacher.phone == data.phone, Teacher.deleted_at.is_(None)
        )
    )
    if existing is not None:
        raise Conflict("A teacher with this phone already exists", code="TEACHER_EXISTS")
    return upsert_teacher(ctx, data)[0]


def update_teacher(ctx: Ctx, teacher_id: uuid.UUID, data: TeacherUpdate) -> Teacher:
    t = get_teacher(ctx, teacher_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    ctx.db.flush()
    return t


def delete_teacher(ctx: Ctx, teacher_id: uuid.UUID) -> None:
    t = get_teacher(ctx, teacher_id)
    t.deleted_at = _now()
    ctx.db.execute(
        delete(TeacherAssignment).where(
            TeacherAssignment.teacher_id == t.id, TeacherAssignment.school_id == ctx.school_id
        )
    )
    deactivate_roles(ctx.db, ctx.school_id, teacher_id=t.id)


# ---------------------------------------------------- teacher assignments
def _assignment_stmt(ctx: Ctx) -> Any:
    return (
        select(TeacherAssignment, Teacher.full_name, Section.name, SchoolClass.name, Subject.name)
        .join(Teacher, Teacher.id == TeacherAssignment.teacher_id)
        .join(Section, Section.id == TeacherAssignment.section_id)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .join(Subject, Subject.id == TeacherAssignment.subject_id)
        .where(TeacherAssignment.school_id == ctx.school_id)
        .order_by(SchoolClass.sort_order, Section.name, Subject.name)
    )


def _assignment_out(row: Any) -> AssignmentOut:
    a, tname, sname, cname, subname = row
    return AssignmentOut(
        id=a.id,
        teacher_id=a.teacher_id,
        teacher_name=tname,
        section_id=a.section_id,
        section_name=section_label(cname, sname),
        subject_id=a.subject_id,
        subject_name=subname,
    )


def list_assignments(
    ctx: Ctx,
    *,
    teacher_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    academic_year_id: uuid.UUID | None = None,
) -> list[AssignmentOut]:
    stmt = _assignment_stmt(ctx)
    if teacher_id:
        stmt = stmt.where(TeacherAssignment.teacher_id == teacher_id)
    if section_id:
        stmt = stmt.where(TeacherAssignment.section_id == section_id)
    if academic_year_id:
        stmt = stmt.where(Section.academic_year_id == academic_year_id)
    return [_assignment_out(r) for r in ctx.db.execute(stmt).all()]


def create_assignment(ctx: Ctx, data: AssignmentIn) -> AssignmentOut:
    get_teacher(ctx, data.teacher_id)
    get_owned(ctx, Section, data.section_id, "Section")
    get_owned(ctx, Subject, data.subject_id, "Subject")
    a = TeacherAssignment(school_id=ctx.school_id, **data.model_dump())
    ctx.db.add(a)
    flush_or_conflict(ctx.db, "This teacher is already assigned to this section and subject")
    return _assignment_out(ctx.db.execute(_assignment_stmt(ctx).where(TeacherAssignment.id == a.id)).one())


def delete_assignment(ctx: Ctx, assignment_id: uuid.UUID) -> None:
    a = get_owned(ctx, TeacherAssignment, assignment_id, "Assignment")
    ctx.db.delete(a)
    ctx.db.flush()


# --------------------------------------------------------------- students
def _student_stmt(ctx: Ctx, academic_year_id: uuid.UUID | None) -> Any:
    enrol = aliased(StudentEnrolment)
    join_cond = enrol.student_id == Student.id
    if academic_year_id:
        join_cond = join_cond & (enrol.academic_year_id == academic_year_id)
    else:
        # Latest enrolment (current year if set up properly).
        latest = (
            select(StudentEnrolment.id)
            .where(StudentEnrolment.student_id == Student.id)
            .order_by(StudentEnrolment.created_at.desc())
            .limit(1)
            .correlate(Student)
            .scalar_subquery()
        )
        join_cond = join_cond & (enrol.id == latest)
    return (
        select(Student, enrol, Section, SchoolClass)
        .select_from(Student)
        .outerjoin(enrol, join_cond)
        .outerjoin(Section, Section.id == enrol.section_id)
        .outerjoin(SchoolClass, SchoolClass.id == Section.class_id)
        .where(Student.school_id == ctx.school_id, Student.deleted_at.is_(None))
    )


def _student_out(row: Any) -> StudentOut:
    s, e, sec, cls = row
    return StudentOut(
        id=s.id,
        admission_no=s.admission_no,
        full_name=s.full_name,
        date_of_birth=s.date_of_birth,
        gender=s.gender,
        section_id=sec.id if sec else None,
        section_name=section_label(cls.name, sec.name) if sec and cls else None,
        class_id=cls.id if cls else None,
        roll_no=e.roll_no if e else None,
        has_pin=s.pin_hash is not None,
    )


def list_students(
    ctx: Ctx,
    params: PageParams,
    *,
    section_id: uuid.UUID | None = None,
    academic_year_id: uuid.UUID | None = None,
    q: str | None = None,
) -> Page[StudentOut]:
    stmt = _student_stmt(ctx, academic_year_id)
    if section_id:
        stmt = stmt.where(Section.id == section_id)
    if q:
        stmt = stmt.where(or_(Student.full_name.ilike(_like(q)), Student.admission_no.ilike(_like(q))))
    stmt = stmt.order_by(SchoolClass.sort_order.nulls_last(), Section.name, Student.full_name)
    rows, total = _paginate(ctx, stmt, params)
    return Page(items=[_student_out(r) for r in rows], total=total, page=params.page, page_size=params.page_size)


def get_student_row(ctx: Ctx, student_id: uuid.UUID) -> StudentOut:
    row = ctx.db.execute(_student_stmt(ctx, None).where(Student.id == student_id)).first()
    if row is None:
        raise NotFound("Student")
    return _student_out(row)


def student_detail(ctx: Ctx, student_id: uuid.UUID) -> StudentDetail:
    base = get_student_row(ctx, student_id)
    return StudentDetail(**base.model_dump(), guardians=list_student_guardians(ctx, student_id))


def _enrol(ctx: Ctx, student: Student, section_id: uuid.UUID, roll_no: str | None) -> None:
    section = get_owned(ctx, Section, section_id, "Section")
    e = ctx.db.scalar(
        select(StudentEnrolment).where(
            StudentEnrolment.student_id == student.id, StudentEnrolment.academic_year_id == section.academic_year_id
        )
    )
    if e is None:
        ctx.db.add(
            StudentEnrolment(
                school_id=ctx.school_id,
                student_id=student.id,
                academic_year_id=section.academic_year_id,
                section_id=section.id,
                roll_no=roll_no,
            )
        )
    else:
        e.section_id = section.id
        e.roll_no = roll_no if roll_no is not None else e.roll_no
    ctx.db.flush()


def upsert_student(ctx: Ctx, data: StudentIn) -> tuple[Student, bool]:
    """Create or update by natural key (school, admission_no)."""
    s = ctx.db.scalar(
        select(Student).where(Student.school_id == ctx.school_id, Student.admission_no == data.admission_no)
    )
    created = s is None
    fields = data.model_dump(exclude={"section_id", "roll_no"})
    if s is None:
        s = Student(school_id=ctx.school_id, **fields)
        ctx.db.add(s)
    else:
        for k, v in fields.items():
            setattr(s, k, v)
        s.deleted_at = None
    ctx.db.flush()
    _enrol(ctx, s, data.section_id, data.roll_no)
    return s, created


def create_student(ctx: Ctx, data: StudentIn) -> StudentOut:
    if ctx.db.scalar(
        select(Student.id).where(
            Student.school_id == ctx.school_id, Student.admission_no == data.admission_no, Student.deleted_at.is_(None)
        )
    ):
        raise Conflict("A student with this admission number already exists", code="STUDENT_EXISTS")
    s, _ = upsert_student(ctx, data)
    return get_student_row(ctx, s.id)


def _get_student(ctx: Ctx, student_id: uuid.UUID) -> Student:
    s = get_owned(ctx, Student, student_id, "Student")
    if s.deleted_at is not None:
        raise NotFound("Student")
    return s


def update_student(ctx: Ctx, student_id: uuid.UUID, data: StudentUpdate) -> StudentOut:
    s = _get_student(ctx, student_id)
    fields = data.model_dump(exclude_unset=True)
    section_id, roll_no = fields.pop("section_id", None), fields.pop("roll_no", None)
    for k, v in fields.items():
        setattr(s, k, v)
    if section_id is not None:
        _enrol(ctx, s, section_id, roll_no)
    elif roll_no is not None:
        current = get_student_row(ctx, s.id)
        if current.section_id is None:
            raise ValidationFailed("Assign a section before setting a roll number")
        _enrol(ctx, s, current.section_id, roll_no)
    ctx.db.flush()
    return get_student_row(ctx, s.id)


def delete_student(ctx: Ctx, student_id: uuid.UUID) -> None:
    s = _get_student(ctx, student_id)
    s.deleted_at = _now()
    deactivate_roles(ctx.db, ctx.school_id, student_id=s.id)


def set_student_pin(ctx: Ctx, student_id: uuid.UUID, pin: str) -> None:
    s = _get_student(ctx, student_id)
    s.pin_hash = hash_pin(pin)
    s.failed_logins = 0
    s.locked_until = None
    if s.user_id is None:
        user = get_or_create_user(ctx.db, None, s.full_name)
        s.user_id = user.id
    ensure_role(ctx.db, s.user_id, RoleType.STUDENT, ctx.school_id, student_id=s.id)
    audit.record(ctx, audit.Action.PIN_RESET, entity="student", entity_id=s.id)


# -------------------------------------------------------------- guardians
def list_guardians(ctx: Ctx, params: PageParams, q: str | None = None) -> Page[GuardianOut]:
    stmt = select(Guardian).where(Guardian.school_id == ctx.school_id, Guardian.deleted_at.is_(None))
    if q:
        stmt = stmt.where(or_(Guardian.full_name.ilike(_like(q)), Guardian.phone.ilike(_like(q))))
    rows, total = _paginate(ctx, stmt.order_by(Guardian.full_name), params)
    return Page(
        items=[GuardianOut.model_validate(r[0]) for r in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def get_guardian(ctx: Ctx, guardian_id: uuid.UUID) -> Guardian:
    g = get_owned(ctx, Guardian, guardian_id, "Guardian")
    if g.deleted_at is not None:
        raise NotFound("Guardian")
    return g


def upsert_guardian(ctx: Ctx, data: GuardianIn) -> tuple[Guardian, bool]:
    g = ctx.db.scalar(select(Guardian).where(Guardian.school_id == ctx.school_id, Guardian.phone == data.phone))
    created = g is None
    if g is None:
        g = Guardian(school_id=ctx.school_id, **data.model_dump())
        ctx.db.add(g)
    else:
        g.full_name = data.full_name
        g.email = data.email or g.email
        g.deleted_at = None
    ctx.db.flush()
    user = get_or_create_user(ctx.db, data.phone, data.full_name)
    g.user_id = user.id
    ensure_role(ctx.db, user.id, RoleType.PARENT, ctx.school_id, guardian_id=g.id)
    return g, created


def create_guardian(ctx: Ctx, data: GuardianIn) -> Guardian:
    if ctx.db.scalar(
        select(Guardian.id).where(
            Guardian.school_id == ctx.school_id, Guardian.phone == data.phone, Guardian.deleted_at.is_(None)
        )
    ):
        raise Conflict("A parent with this phone already exists", code="GUARDIAN_EXISTS")
    return upsert_guardian(ctx, data)[0]


def update_guardian(ctx: Ctx, guardian_id: uuid.UUID, data: GuardianUpdate) -> Guardian:
    g = get_guardian(ctx, guardian_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(g, k, v)
    ctx.db.flush()
    return g


def delete_guardian(ctx: Ctx, guardian_id: uuid.UUID) -> None:
    g = get_guardian(ctx, guardian_id)
    g.deleted_at = _now()
    ctx.db.execute(
        delete(StudentGuardian).where(StudentGuardian.guardian_id == g.id, StudentGuardian.school_id == ctx.school_id)
    )
    deactivate_roles(ctx.db, ctx.school_id, guardian_id=g.id)


def list_student_guardians(ctx: Ctx, student_id: uuid.UUID) -> list[StudentGuardianOut]:
    rows = ctx.db.execute(
        select(StudentGuardian, Guardian)
        .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
        .where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.school_id == ctx.school_id,
            Guardian.deleted_at.is_(None),
        )
        .order_by(StudentGuardian.is_primary.desc(), Guardian.full_name)
    ).all()
    return [
        StudentGuardianOut(
            guardian_id=g.id, full_name=g.full_name, phone=g.phone, relation=sg.relation, is_primary=sg.is_primary
        )
        for sg, g in rows
    ]


def link_guardian(ctx: Ctx, student_id: uuid.UUID, data: GuardianLinkIn) -> list[StudentGuardianOut]:
    s = _get_student(ctx, student_id)
    if data.guardian is not None:
        g, _ = upsert_guardian(ctx, data.guardian)
    else:
        assert data.guardian_id is not None
        g = get_guardian(ctx, data.guardian_id)
    link_guardian_ids(ctx, s.id, g.id, data.relation, data.is_primary)
    return list_student_guardians(ctx, s.id)


def link_guardian_ids(ctx: Ctx, student_id: uuid.UUID, guardian_id: uuid.UUID, relation: Any, is_primary: bool) -> None:
    link = ctx.db.scalar(
        select(StudentGuardian).where(
            StudentGuardian.student_id == student_id, StudentGuardian.guardian_id == guardian_id
        )
    )
    if link is None:
        ctx.db.add(
            StudentGuardian(
                school_id=ctx.school_id,
                student_id=student_id,
                guardian_id=guardian_id,
                relation=relation,
                is_primary=is_primary,
            )
        )
    else:
        link.relation, link.is_primary = relation, is_primary
    ctx.db.flush()


def unlink_guardian(ctx: Ctx, student_id: uuid.UUID, guardian_id: uuid.UUID) -> None:
    _get_student(ctx, student_id)
    result = ctx.db.execute(
        delete(StudentGuardian).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.guardian_id == guardian_id,
            StudentGuardian.school_id == ctx.school_id,
        )
    )
    if not getattr(result, "rowcount", 0):
        raise NotFound("Guardian link")
