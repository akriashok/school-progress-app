"""Academic structure: years, classes, subjects, sections, section subjects, grade scales."""

import uuid
from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Ctx
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import (
    AcademicYear,
    Base,
    Exam,
    GradeBand,
    GradeScale,
    SchoolClass,
    Section,
    SectionSubject,
    StudentEnrolment,
    Subject,
    Teacher,
)
from app.schemas.setup import (
    AcademicYearIn,
    ClassIn,
    GradeBandOut,
    GradeScaleIn,
    GradeScaleOut,
    SectionIn,
    SectionOut,
    SectionUpdate,
    SubjectIn,
)
from app.services import grading

M = TypeVar("M", bound=Base)


def get_owned[M: Base](ctx: Ctx, model: type[M], obj_id: uuid.UUID, label: str) -> M:
    """Fetch a school-owned row by id, scoped to the caller's school (404 otherwise)."""
    cols: Any = model  # every school-owned model has id + school_id columns
    obj: M | None = ctx.db.scalars(select(model).where(cols.id == obj_id, cols.school_id == ctx.school_id)).first()
    if obj is None:
        raise NotFound(label)
    return obj


def flush_or_conflict(db: Session, message: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise Conflict(message) from exc


def delete_or_conflict(ctx: Ctx, obj: Base, message: str) -> None:
    ctx.db.delete(obj)
    flush_or_conflict(ctx.db, message)


# --------------------------------------------------------- academic years
def list_years(ctx: Ctx) -> Sequence[AcademicYear]:
    return ctx.db.scalars(
        select(AcademicYear).where(AcademicYear.school_id == ctx.school_id).order_by(AcademicYear.start_date.desc())
    ).all()


def current_year(ctx: Ctx) -> AcademicYear | None:
    return ctx.db.scalar(
        select(AcademicYear).where(AcademicYear.school_id == ctx.school_id, AcademicYear.is_current.is_(True))
    )


def _clear_current(ctx: Ctx, except_id: uuid.UUID | None = None) -> None:
    stmt = update(AcademicYear).where(AcademicYear.school_id == ctx.school_id, AcademicYear.is_current.is_(True))
    if except_id:
        stmt = stmt.where(AcademicYear.id != except_id)
    ctx.db.execute(stmt.values(is_current=False))


def create_year(ctx: Ctx, data: AcademicYearIn) -> AcademicYear:
    if data.is_current:
        _clear_current(ctx)
    year = AcademicYear(school_id=ctx.school_id, **data.model_dump())
    ctx.db.add(year)
    flush_or_conflict(ctx.db, "An academic year with this name already exists")
    return year


def update_year(ctx: Ctx, year_id: uuid.UUID, data: AcademicYearIn) -> AcademicYear:
    year = get_owned(ctx, AcademicYear, year_id, "Academic year")
    if data.is_current:
        _clear_current(ctx, except_id=year.id)
        ctx.db.flush()
    for k, v in data.model_dump().items():
        setattr(year, k, v)
    flush_or_conflict(ctx.db, "An academic year with this name already exists")
    return year


def delete_year(ctx: Ctx, year_id: uuid.UUID) -> None:
    year = get_owned(ctx, AcademicYear, year_id, "Academic year")
    delete_or_conflict(ctx, year, "This year has sections or exams; remove them first")


# ---------------------------------------------------------------- classes
def list_classes(ctx: Ctx) -> Sequence[SchoolClass]:
    return ctx.db.scalars(
        select(SchoolClass).where(SchoolClass.school_id == ctx.school_id).order_by(SchoolClass.sort_order)
    ).all()


def create_class(ctx: Ctx, data: ClassIn) -> SchoolClass:
    c = SchoolClass(school_id=ctx.school_id, **data.model_dump())
    ctx.db.add(c)
    flush_or_conflict(ctx.db, "A class with this name already exists")
    return c


def update_class(ctx: Ctx, class_id: uuid.UUID, data: ClassIn) -> SchoolClass:
    c = get_owned(ctx, SchoolClass, class_id, "Class")
    c.name, c.sort_order = data.name, data.sort_order
    flush_or_conflict(ctx.db, "A class with this name already exists")
    return c


def delete_class(ctx: Ctx, class_id: uuid.UUID) -> None:
    delete_or_conflict(
        ctx,
        get_owned(ctx, SchoolClass, class_id, "Class"),
        "This class has sections or exam subjects; remove them first",
    )


# --------------------------------------------------------------- subjects
def list_subjects(ctx: Ctx) -> Sequence[Subject]:
    return ctx.db.scalars(select(Subject).where(Subject.school_id == ctx.school_id).order_by(Subject.name)).all()


def create_subject(ctx: Ctx, data: SubjectIn) -> Subject:
    s = Subject(school_id=ctx.school_id, **data.model_dump())
    ctx.db.add(s)
    flush_or_conflict(ctx.db, "A subject with this name already exists")
    return s


def update_subject(ctx: Ctx, subject_id: uuid.UUID, data: SubjectIn) -> Subject:
    s = get_owned(ctx, Subject, subject_id, "Subject")
    s.name, s.code = data.name, data.code
    flush_or_conflict(ctx.db, "A subject with this name already exists")
    return s


def delete_subject(ctx: Ctx, subject_id: uuid.UUID) -> None:
    delete_or_conflict(
        ctx,
        get_owned(ctx, Subject, subject_id, "Subject"),
        "This subject is in use; remove it from sections and exams first",
    )


# --------------------------------------------------------------- sections
def section_rows(
    ctx: Ctx,
    *,
    academic_year_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    section_ids: Sequence[uuid.UUID] | None = None,
) -> list[SectionOut]:
    counts = (
        select(StudentEnrolment.section_id, func.count().label("n"))
        .where(StudentEnrolment.school_id == ctx.school_id)
        .group_by(StudentEnrolment.section_id)
        .subquery()
    )
    stmt = (
        select(Section, SchoolClass, Teacher.full_name, func.coalesce(counts.c.n, 0))
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .outerjoin(Teacher, Teacher.id == Section.class_teacher_id)
        .outerjoin(counts, counts.c.section_id == Section.id)
        .where(Section.school_id == ctx.school_id)
        .order_by(SchoolClass.sort_order, Section.name)
    )
    if academic_year_id:
        stmt = stmt.where(Section.academic_year_id == academic_year_id)
    if class_id:
        stmt = stmt.where(Section.class_id == class_id)
    if section_ids is not None:
        stmt = stmt.where(Section.id.in_(section_ids))
    return [
        SectionOut(
            id=s.id,
            academic_year_id=s.academic_year_id,
            class_id=c.id,
            class_name=c.name,
            class_sort_order=c.sort_order,
            name=s.name,
            display_name=section_label(c.name, s.name),
            class_teacher_id=s.class_teacher_id,
            class_teacher_name=t,
            student_count=int(n),
        )
        for s, c, t, n in ctx.db.execute(stmt).all()
    ]


def section_label(class_name: str, section_name: str) -> str:
    prefix = "Class " if class_name[:1].isdigit() else ""
    return f"{prefix}{class_name}-{section_name}"


def get_section_out(ctx: Ctx, section_id: uuid.UUID) -> SectionOut:
    rows = section_rows(ctx, section_ids=[section_id])
    if not rows:
        raise NotFound("Section")
    return rows[0]


def _check_teacher(ctx: Ctx, teacher_id: uuid.UUID | None) -> None:
    if teacher_id is not None:
        t = get_owned(ctx, Teacher, teacher_id, "Teacher")
        if t.deleted_at is not None:
            raise NotFound("Teacher")


def create_section(ctx: Ctx, data: SectionIn) -> SectionOut:
    get_owned(ctx, AcademicYear, data.academic_year_id, "Academic year")
    get_owned(ctx, SchoolClass, data.class_id, "Class")
    _check_teacher(ctx, data.class_teacher_id)
    s = Section(school_id=ctx.school_id, **data.model_dump())
    ctx.db.add(s)
    flush_or_conflict(ctx.db, "This section already exists for the class and year")
    return get_section_out(ctx, s.id)


def update_section(ctx: Ctx, section_id: uuid.UUID, data: SectionUpdate) -> SectionOut:
    s = get_owned(ctx, Section, section_id, "Section")
    fields = data.model_dump(exclude_unset=True)
    if "class_teacher_id" in fields:
        _check_teacher(ctx, fields["class_teacher_id"])
    for k, v in fields.items():
        setattr(s, k, v)
    flush_or_conflict(ctx.db, "This section already exists for the class and year")
    return get_section_out(ctx, s.id)


def delete_section(ctx: Ctx, section_id: uuid.UUID) -> None:
    delete_or_conflict(
        ctx, get_owned(ctx, Section, section_id, "Section"), "This section has students or marks; move them first"
    )


def section_subjects(ctx: Ctx, section_id: uuid.UUID) -> Sequence[Subject]:
    get_owned(ctx, Section, section_id, "Section")
    return ctx.db.scalars(
        select(Subject)
        .join(SectionSubject, SectionSubject.subject_id == Subject.id)
        .where(SectionSubject.section_id == section_id, SectionSubject.school_id == ctx.school_id)
        .order_by(Subject.name)
    ).all()


def set_section_subjects(ctx: Ctx, section_id: uuid.UUID, subject_ids: list[uuid.UUID]) -> Sequence[Subject]:
    get_owned(ctx, Section, section_id, "Section")
    wanted = set(subject_ids)
    for sid in wanted:
        get_owned(ctx, Subject, sid, "Subject")
    ctx.db.execute(
        delete(SectionSubject).where(
            SectionSubject.section_id == section_id,
            SectionSubject.school_id == ctx.school_id,
            SectionSubject.subject_id.not_in(wanted),
        )
    )
    existing = set(
        ctx.db.scalars(select(SectionSubject.subject_id).where(SectionSubject.section_id == section_id)).all()
    )
    for sid in wanted - existing:
        ctx.db.add(SectionSubject(school_id=ctx.school_id, section_id=section_id, subject_id=sid))
    ctx.db.flush()
    return section_subjects(ctx, section_id)


# ----------------------------------------------------------- grade scales
def _scale_out(db: Session, scale: GradeScale) -> GradeScaleOut:
    bands = db.scalars(
        select(GradeBand).where(GradeBand.grade_scale_id == scale.id).order_by(GradeBand.min_percent.desc())
    ).all()
    return GradeScaleOut(
        id=scale.id, name=scale.name, is_default=scale.is_default, bands=[GradeBandOut.model_validate(b) for b in bands]
    )


def list_scales(ctx: Ctx) -> list[GradeScaleOut]:
    scales = ctx.db.scalars(
        select(GradeScale).where(GradeScale.school_id == ctx.school_id).order_by(GradeScale.name)
    ).all()
    return [_scale_out(ctx.db, s) for s in scales]


def _validate_scale(data: GradeScaleIn) -> None:
    problems = grading.validate_bands([(b.grade, b.min_percent, b.max_percent) for b in data.bands])
    if any(b.min_percent > b.max_percent for b in data.bands):
        problems.append("min_percent must be <= max_percent")
    if problems:
        raise ValidationFailed("Grade bands are not valid", details=problems)


def _write_scale(ctx: Ctx, scale: GradeScale, data: GradeScaleIn) -> GradeScaleOut:
    if data.is_default:
        ctx.db.execute(
            update(GradeScale)
            .where(GradeScale.school_id == ctx.school_id, GradeScale.id != scale.id)
            .values(is_default=False)
        )
        ctx.db.flush()
    scale.name, scale.is_default = data.name, data.is_default
    ctx.db.execute(delete(GradeBand).where(GradeBand.grade_scale_id == scale.id))
    for b in data.bands:
        ctx.db.add(GradeBand(grade_scale_id=scale.id, **b.model_dump()))
    flush_or_conflict(ctx.db, "A grade scale with this name already exists")
    return _scale_out(ctx.db, scale)


def create_scale(ctx: Ctx, data: GradeScaleIn) -> GradeScaleOut:
    _validate_scale(data)
    scale = GradeScale(school_id=ctx.school_id, name=data.name, is_default=False)
    ctx.db.add(scale)
    flush_or_conflict(ctx.db, "A grade scale with this name already exists")
    return _write_scale(ctx, scale, data)


def update_scale(ctx: Ctx, scale_id: uuid.UUID, data: GradeScaleIn) -> GradeScaleOut:
    _validate_scale(data)
    return _write_scale(ctx, get_owned(ctx, GradeScale, scale_id, "Grade scale"), data)


def delete_scale(ctx: Ctx, scale_id: uuid.UUID) -> None:
    scale = get_owned(ctx, GradeScale, scale_id, "Grade scale")
    if scale.is_default:
        raise ValidationFailed("Make another scale the default before deleting this one")
    in_use = ctx.db.scalar(select(func.count()).select_from(Exam).where(Exam.grade_scale_id == scale.id))
    if in_use:
        raise Conflict("This grade scale is used by exams")
    delete_or_conflict(ctx, scale, "This grade scale is in use")


def model_dict(obj: Any, *fields: str) -> dict[str, Any]:
    return {f: getattr(obj, f) for f in fields}
