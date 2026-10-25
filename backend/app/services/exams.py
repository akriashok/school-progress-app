"""Exams, exam subjects and the marks-entry status matrix."""

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, exists, func, or_, select

from app.core.deps import Ctx
from app.core.errors import Conflict, NotFound
from app.models import (
    AcademicYear,
    Exam,
    ExamSubject,
    GradeScale,
    Mark,
    MarksSubmission,
    ResultPublication,
    School,
    SchoolClass,
    Section,
    SectionSubject,
    StudentEnrolment,
    Subject,
    Teacher,
    TeacherAssignment,
)
from app.schemas.exams import (
    AutoExamSubjectsIn,
    ExamIn,
    ExamStatus,
    ExamStatusRow,
    ExamSubjectIn,
    ExamSubjectOut,
    ExamUpdate,
)
from app.services.academics import flush_or_conflict, get_owned, section_label
from app.services.grading import pass_marks_for


def list_exams(ctx: Ctx, academic_year_id: uuid.UUID | None = None) -> Sequence[Exam]:
    stmt = select(Exam).where(Exam.school_id == ctx.school_id)
    if academic_year_id:
        stmt = stmt.where(Exam.academic_year_id == academic_year_id)
    else:
        stmt = stmt.join(AcademicYear, AcademicYear.id == Exam.academic_year_id).order_by(
            AcademicYear.start_date.desc()
        )
    return ctx.db.scalars(stmt.order_by(Exam.sequence)).all()


def get_exam(ctx: Ctx, exam_id: uuid.UUID) -> Exam:
    return get_owned(ctx, Exam, exam_id, "Exam")


def create_exam(ctx: Ctx, data: ExamIn) -> Exam:
    get_owned(ctx, AcademicYear, data.academic_year_id, "Academic year")
    if data.grade_scale_id:
        get_owned(ctx, GradeScale, data.grade_scale_id, "Grade scale")
    exam = Exam(school_id=ctx.school_id, **data.model_dump())
    ctx.db.add(exam)
    flush_or_conflict(ctx.db, "An exam with this name already exists in the year")
    return exam


def update_exam(ctx: Ctx, exam_id: uuid.UUID, data: ExamUpdate) -> Exam:
    exam = get_exam(ctx, exam_id)
    fields = data.model_dump(exclude_unset=True)
    if fields.get("grade_scale_id"):
        get_owned(ctx, GradeScale, fields["grade_scale_id"], "Grade scale")
    for k, v in fields.items():
        setattr(exam, k, v)
    flush_or_conflict(ctx.db, "An exam with this name already exists in the year")
    return exam


def delete_exam(ctx: Ctx, exam_id: uuid.UUID) -> None:
    exam = get_exam(ctx, exam_id)
    has_marks = ctx.db.scalar(
        select(exists().where(Mark.exam_subject_id.in_(select(ExamSubject.id).where(ExamSubject.exam_id == exam.id))))
    )
    if has_marks:
        raise Conflict("This exam already has marks and cannot be deleted", code="EXAM_HAS_MARKS")
    ctx.db.delete(exam)
    ctx.db.flush()


# --------------------------------------------------------- exam subjects
def _pass_percent(ctx: Ctx) -> Decimal:
    return ctx.db.scalar(select(School.pass_percent).where(School.id == ctx.school_id)) or Decimal(33)


def exam_subject_rows(ctx: Ctx, exam_id: uuid.UUID, es_ids: Sequence[uuid.UUID] | None = None) -> list[ExamSubjectOut]:
    pp = _pass_percent(ctx)
    stmt = (
        select(ExamSubject, SchoolClass.name, Subject.name)
        .join(SchoolClass, SchoolClass.id == ExamSubject.class_id)
        .join(Subject, Subject.id == ExamSubject.subject_id)
        .where(ExamSubject.school_id == ctx.school_id, ExamSubject.exam_id == exam_id)
        .order_by(SchoolClass.sort_order, Subject.name)
    )
    if es_ids is not None:
        stmt = stmt.where(ExamSubject.id.in_(es_ids))
    return [
        ExamSubjectOut(
            id=es.id,
            exam_id=es.exam_id,
            class_id=es.class_id,
            class_name=cn,
            subject_id=es.subject_id,
            subject_name=sn,
            max_marks=es.max_marks,
            pass_marks=es.pass_marks,
            effective_pass_marks=pass_marks_for(es.max_marks, es.pass_marks, pp).quantize(Decimal("0.01")),
            exam_date=es.exam_date,
        )
        for es, cn, sn in ctx.db.execute(stmt).all()
    ]


def upsert_exam_subjects(ctx: Ctx, exam_id: uuid.UUID, items: list[ExamSubjectIn]) -> list[ExamSubjectOut]:
    get_exam(ctx, exam_id)
    for item in items:
        get_owned(ctx, SchoolClass, item.class_id, "Class")
        get_owned(ctx, Subject, item.subject_id, "Subject")
        es = ctx.db.scalar(
            select(ExamSubject).where(
                ExamSubject.exam_id == exam_id,
                ExamSubject.class_id == item.class_id,
                ExamSubject.subject_id == item.subject_id,
            )
        )
        if es is None:
            ctx.db.add(ExamSubject(school_id=ctx.school_id, exam_id=exam_id, **item.model_dump()))
        else:
            es.max_marks, es.pass_marks, es.exam_date = item.max_marks, item.pass_marks, item.exam_date
    ctx.db.flush()
    return exam_subject_rows(ctx, exam_id)


def auto_exam_subjects(ctx: Ctx, exam_id: uuid.UUID, data: AutoExamSubjectsIn) -> list[ExamSubjectOut]:
    """Create exam subjects for every (class, subject) studied in the exam's year."""
    exam = get_exam(ctx, exam_id)
    stmt = (
        select(Section.class_id, SectionSubject.subject_id)
        .distinct()
        .join(SectionSubject, SectionSubject.section_id == Section.id)
        .where(Section.school_id == ctx.school_id, Section.academic_year_id == exam.academic_year_id)
    )
    if data.class_ids:
        stmt = stmt.where(Section.class_id.in_(data.class_ids))
    items = [
        ExamSubjectIn(class_id=c, subject_id=s, max_marks=data.max_marks, pass_marks=data.pass_marks)
        for c, s in ctx.db.execute(stmt).all()
    ]
    existing = {
        (es.class_id, es.subject_id) for es in ctx.db.scalars(select(ExamSubject).where(ExamSubject.exam_id == exam.id))
    }
    new_items = [i for i in items if (i.class_id, i.subject_id) not in existing]
    if new_items:
        return upsert_exam_subjects(ctx, exam_id, new_items)
    return exam_subject_rows(ctx, exam_id)


def delete_exam_subject(ctx: Ctx, exam_id: uuid.UUID, es_id: uuid.UUID) -> None:
    es = get_owned(ctx, ExamSubject, es_id, "Exam subject")
    if es.exam_id != exam_id:
        raise NotFound("Exam subject")
    if ctx.db.scalar(select(exists().where(Mark.exam_subject_id == es.id))):
        raise Conflict("Marks have been entered for this subject", code="EXAM_SUBJECT_HAS_MARKS")
    ctx.db.delete(es)
    ctx.db.flush()


# ----------------------------------------------------- applicability
def applicable_pairs(ctx: Ctx, exam: Exam, section_ids: Sequence[uuid.UUID] | None = None) -> list[Any]:
    """(Section, ExamSubject) pairs that need marks for this exam.

    A subject applies to a section if the exam has it for the section's class and
    the section studies it (or the section has no subject list configured).
    """
    has_list = exists().where(SectionSubject.section_id == Section.id)
    studies = exists().where(
        SectionSubject.section_id == Section.id, SectionSubject.subject_id == ExamSubject.subject_id
    )
    stmt = (
        select(Section, ExamSubject, SchoolClass, Subject)
        .join(ExamSubject, and_(ExamSubject.class_id == Section.class_id, ExamSubject.exam_id == exam.id))
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .join(Subject, Subject.id == ExamSubject.subject_id)
        .where(
            Section.school_id == ctx.school_id,
            Section.academic_year_id == exam.academic_year_id,
            or_(~has_list, studies),
        )
        .order_by(SchoolClass.sort_order, Section.name, Subject.name)
    )
    if section_ids is not None:
        stmt = stmt.where(Section.id.in_(section_ids))
    return list(ctx.db.execute(stmt).all())


def exam_status(ctx: Ctx, exam_id: uuid.UUID) -> ExamStatus:
    exam = get_exam(ctx, exam_id)
    pairs = applicable_pairs(ctx, exam)
    sid = ctx.school_id

    students = dict(
        ctx.db.execute(
            select(StudentEnrolment.section_id, func.count())
            .where(StudentEnrolment.school_id == sid, StudentEnrolment.academic_year_id == exam.academic_year_id)
            .group_by(StudentEnrolment.section_id)
        ).all()
    )
    entered = {
        (s, e): n
        for s, e, n in ctx.db.execute(
            select(Mark.section_id, Mark.exam_subject_id, func.count())
            .join(ExamSubject, ExamSubject.id == Mark.exam_subject_id)
            .where(Mark.school_id == sid, ExamSubject.exam_id == exam.id)
            .group_by(Mark.section_id, Mark.exam_subject_id)
        ).all()
    }
    submitted = {
        (s.section_id, s.exam_subject_id): s.status
        for s in ctx.db.scalars(
            select(MarksSubmission)
            .join(ExamSubject, ExamSubject.id == MarksSubmission.exam_subject_id)
            .where(MarksSubmission.school_id == sid, ExamSubject.exam_id == exam.id)
        )
    }
    teachers: dict[tuple[uuid.UUID, uuid.UUID], list[str]] = {}
    for sec_id, subj_id, name in ctx.db.execute(
        select(TeacherAssignment.section_id, TeacherAssignment.subject_id, Teacher.full_name)
        .join(Teacher, Teacher.id == TeacherAssignment.teacher_id)
        .where(TeacherAssignment.school_id == sid, Teacher.deleted_at.is_(None))
    ).all():
        teachers.setdefault((sec_id, subj_id), []).append(name)
    published = set(
        ctx.db.scalars(
            select(ResultPublication.section_id).where(
                ResultPublication.exam_id == exam.id, ResultPublication.school_id == sid
            )
        )
    )

    rows: list[ExamStatusRow] = []
    for sec, es, cls, subj in pairs:
        n_entered = entered.get((sec.id, es.id), 0)
        sub = submitted.get((sec.id, es.id))
        state = (
            "SUBMITTED" if sub is not None and sub.value == "SUBMITTED" else ("DRAFT" if n_entered else "NOT_STARTED")
        )
        rows.append(
            ExamStatusRow(
                section_id=sec.id,
                section_name=section_label(cls.name, sec.name),
                class_id=cls.id,
                exam_subject_id=es.id,
                subject_id=subj.id,
                subject_name=subj.name,
                teachers=sorted(teachers.get((sec.id, subj.id), [])),
                students=int(students.get(sec.id, 0)),
                entered=int(n_entered),
                status=state,
                published=sec.id in published,
            )
        )
    n_sub = sum(1 for r in rows if r.status == "SUBMITTED")
    return ExamStatus(exam_id=exam.id, total=len(rows), submitted=n_sub, pending=len(rows) - n_sub, rows=rows)
