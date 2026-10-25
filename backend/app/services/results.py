"""Results for students/parents (and staff drill-down) from v_student_exam_results."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    Numeric,
    Select,
    Table,
    and_,
    exists,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.deps import Ctx
from app.core.errors import NotFound
from app.models import (
    AcademicYear,
    Exam,
    ExamSubject,
    Guardian,
    Mark,
    MarkStatus,
    ResultPublication,
    RoleType,
    School,
    SchoolClass,
    Section,
    Student,
    StudentEnrolment,
    StudentGuardian,
    Subject,
)
from app.schemas.exams import (
    ChildOut,
    ExamResultDetail,
    ExamResultSummary,
    Progress,
    ProgressPoint,
    SubjectResult,
    SubjectSeries,
)
from app.services.academics import section_label
from app.services.grading import Band, grade_for, load_bands, pass_marks_for, round2
from app.services.permissions import ensure_student_visible, only_published

_view_md = MetaData()
results_view = Table(
    "v_student_exam_results",
    _view_md,
    Column("school_id", UUID(as_uuid=True)),
    Column("exam_id", UUID(as_uuid=True)),
    Column("section_id", UUID(as_uuid=True)),
    Column("student_id", UUID(as_uuid=True)),
    Column("total_obtained", Numeric),
    Column("total_max", Numeric),
    Column("subjects_failed", Integer),
    Column("percentage", Numeric),
    Column("passed", Boolean),
    Column("section_rank", Integer),
)
V = results_view.c


def published_clause() -> Any:
    return exists().where(ResultPublication.exam_id == V.exam_id, ResultPublication.section_id == V.section_id)


def _school(ctx: Ctx) -> School:
    school = ctx.db.get(School, ctx.school_id)
    if school is None:
        raise NotFound("School")
    return school


def _show_rank(ctx: Ctx, school: School) -> bool:
    # Staff always see ranks; parents/students only when the school allows it.
    return school.show_rank or ctx.user.is_staff


class _Bands:
    """Cache grade bands per grade scale within a request."""

    def __init__(self, ctx: Ctx) -> None:
        self.ctx = ctx
        self._cache: dict[uuid.UUID | None, list[Band]] = {}

    def for_exam(self, exam: Exam) -> list[Band]:
        key = exam.grade_scale_id
        if key not in self._cache:
            self._cache[key] = load_bands(self.ctx.db, self.ctx.school_id, key)
        return self._cache[key]


def _summary_stmt(ctx: Ctx, student_id: uuid.UUID) -> Select[Any]:
    section_size = (
        select(func.count())
        .select_from(StudentEnrolment)
        .where(StudentEnrolment.section_id == V.section_id)
        .scalar_subquery()
    )
    stmt = (
        select(results_view, Exam, published_clause().label("published"), section_size.label("section_size"))
        .join(Exam, Exam.id == V.exam_id)
        .where(V.school_id == ctx.school_id, V.student_id == student_id)
    )
    if only_published(ctx):
        stmt = stmt.where(published_clause())
    return stmt


def _to_summary(ctx: Ctx, row: Any, exam: Exam, bands: _Bands, show_rank: bool) -> ExamResultSummary:
    pct = round2(row.percentage) if row.percentage is not None else None
    return ExamResultSummary(
        exam_id=exam.id,
        exam_name=exam.name,
        sequence=exam.sequence,
        academic_year_id=exam.academic_year_id,
        section_id=row.section_id,
        total_obtained=round2(row.total_obtained),
        total_max=round2(row.total_max),
        percentage=pct,
        grade=grade_for(pct, bands.for_exam(exam)),
        passed=bool(row.passed),
        subjects_failed=int(row.subjects_failed),
        rank=int(row.section_rank) if show_rank else None,
        section_size=int(row.section_size or 0),
        published=bool(row.published),
    )


def _year_filter(ctx: Ctx, academic_year_id: uuid.UUID | None) -> uuid.UUID | None:
    if academic_year_id:
        return academic_year_id
    return ctx.db.scalar(
        select(AcademicYear.id).where(AcademicYear.school_id == ctx.school_id, AcademicYear.is_current.is_(True))
    )


def student_results(
    ctx: Ctx, student_id: uuid.UUID, academic_year_id: uuid.UUID | None = None
) -> list[ExamResultSummary]:
    ensure_student_visible(ctx, student_id)
    school = _school(ctx)
    bands = _Bands(ctx)
    stmt = _summary_stmt(ctx, student_id)
    if academic_year_id:
        stmt = stmt.where(Exam.academic_year_id == academic_year_id)
    stmt = stmt.join(AcademicYear, AcademicYear.id == Exam.academic_year_id).order_by(
        AcademicYear.start_date.desc(), Exam.sequence.desc()
    )
    show = _show_rank(ctx, school)
    return [_to_summary(ctx, r, r.Exam, bands, show) for r in ctx.db.execute(stmt).all()]


def student_exam_result(ctx: Ctx, student_id: uuid.UUID, exam_id: uuid.UUID) -> ExamResultDetail:
    student = ensure_student_visible(ctx, student_id)
    school = _school(ctx)
    bands = _Bands(ctx)
    row = ctx.db.execute(_summary_stmt(ctx, student_id).where(V.exam_id == exam_id)).first()
    if row is None:
        raise NotFound("Result")
    exam: Exam = row.Exam
    summary = _to_summary(ctx, row, exam, bands, _show_rank(ctx, school))

    subjects: list[SubjectResult] = []
    for m, es, subj in ctx.db.execute(
        select(Mark, ExamSubject, Subject)
        .join(ExamSubject, ExamSubject.id == Mark.exam_subject_id)
        .join(Subject, Subject.id == ExamSubject.subject_id)
        .where(Mark.school_id == ctx.school_id, Mark.student_id == student_id, ExamSubject.exam_id == exam.id)
        .order_by(Subject.name)
    ).all():
        pm = pass_marks_for(es.max_marks, es.pass_marks, school.pass_percent)
        if m.status == MarkStatus.EXEMPT:
            pct, passed = None, None
        else:
            obtained = m.marks_obtained or Decimal(0)
            pct = round2(obtained * 100 / es.max_marks)
            passed = obtained >= pm
        subjects.append(
            SubjectResult(
                subject_id=subj.id,
                subject_name=subj.name,
                max_marks=es.max_marks,
                pass_marks=round2(pm),
                status=m.status,
                marks=m.marks_obtained,
                percentage=pct,
                grade=grade_for(pct, bands.for_exam(exam)),
                passed=passed,
            )
        )
    return ExamResultDetail(
        **summary.model_dump(), student_id=student.id, student_name=student.full_name, subjects=subjects
    )


def student_progress(ctx: Ctx, student_id: uuid.UUID, academic_year_id: uuid.UUID | None = None) -> Progress:
    ensure_student_visible(ctx, student_id)
    year_id = _year_filter(ctx, academic_year_id)
    stmt = _summary_stmt(ctx, student_id).order_by(Exam.sequence)
    if year_id:
        stmt = stmt.where(Exam.academic_year_id == year_id)
    rows = ctx.db.execute(stmt).all()
    overall = [
        ProgressPoint(
            exam_id=r.Exam.id,
            exam_name=r.Exam.name,
            sequence=r.Exam.sequence,
            percentage=round2(r.percentage) if r.percentage is not None else None,
        )
        for r in rows
    ]
    exam_ids = [p.exam_id for p in overall]
    series: dict[uuid.UUID, SubjectSeries] = {}
    if exam_ids:
        for m, es, subj, exam in ctx.db.execute(
            select(Mark, ExamSubject, Subject, Exam)
            .join(ExamSubject, ExamSubject.id == Mark.exam_subject_id)
            .join(Subject, Subject.id == ExamSubject.subject_id)
            .join(Exam, Exam.id == ExamSubject.exam_id)
            .where(Mark.school_id == ctx.school_id, Mark.student_id == student_id, Exam.id.in_(exam_ids))
            .order_by(Subject.name, Exam.sequence)
        ).all():
            pct = (
                None if m.status == MarkStatus.EXEMPT else round2((m.marks_obtained or Decimal(0)) * 100 / es.max_marks)
            )
            s = series.setdefault(subj.id, SubjectSeries(subject_id=subj.id, subject_name=subj.name, points=[]))
            s.points.append(ProgressPoint(exam_id=exam.id, exam_name=exam.name, sequence=exam.sequence, percentage=pct))
    return Progress(student_id=student_id, academic_year_id=year_id, overall=overall, subjects=list(series.values()))


def children(ctx: Ctx) -> list[ChildOut]:
    """Parent's linked children in the active school."""
    if ctx.user.role != RoleType.PARENT or ctx.user.guardian_id is None:
        return []
    school = _school(ctx)
    latest = (
        select(StudentEnrolment.id)
        .where(StudentEnrolment.student_id == Student.id)
        .order_by(StudentEnrolment.created_at.desc())
        .limit(1)
        .correlate(Student)
        .scalar_subquery()
    )
    rows = ctx.db.execute(
        select(Student, StudentGuardian.relation, Section, SchoolClass)
        .select_from(Student)
        .join(StudentGuardian, StudentGuardian.student_id == Student.id)
        .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
        .outerjoin(StudentEnrolment, and_(StudentEnrolment.student_id == Student.id, StudentEnrolment.id == latest))
        .outerjoin(Section, Section.id == StudentEnrolment.section_id)
        .outerjoin(SchoolClass, SchoolClass.id == Section.class_id)
        .where(
            StudentGuardian.guardian_id == ctx.user.guardian_id,
            StudentGuardian.school_id == ctx.school_id,
            Student.deleted_at.is_(None),
        )
        .order_by(Student.full_name)
    ).all()
    return [
        ChildOut(
            student_id=s.id,
            full_name=s.full_name,
            admission_no=s.admission_no,
            section_name=section_label(c.name, sec.name) if sec and c else None,
            school_name=school.name,
            relation=rel.value if rel else None,
        )
        for s, rel, sec, c in rows
    ]
