"""Principal / admin dashboards (MVP_SPEC §5.6). Staff see draft + published marks."""

import uuid
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select

from app.core.deps import Ctx
from app.models import (
    Exam,
    ExamSubject,
    Mark,
    MarkStatus,
    ResultPublication,
    School,
    SchoolClass,
    Section,
    Student,
    StudentEnrolment,
    Subject,
)
from app.schemas.exams import (
    AttentionStudent,
    DashboardSummary,
    GradeCount,
    SectionPerformance,
    SectionStudentResult,
    SubjectPerformance,
    Topper,
)
from app.services.academics import get_owned, section_label
from app.services.grading import grade_for, load_bands, round2
from app.services.permissions import ensure_section_in_school
from app.services.results import V, results_view

ATTENTION_FAILS = 2
ATTENTION_DROP = Decimal(10)


def _pct(num: Any, den: Any) -> Decimal | None:
    if not den:
        return None
    return round2(Decimal(num) * 100 / Decimal(den))


def _avg(v: Any) -> Decimal | None:
    return round2(v) if v is not None else None


def _sections(ctx: Ctx, exam: Exam) -> dict[uuid.UUID, tuple[Section, SchoolClass]]:
    rows = ctx.db.execute(
        select(Section, SchoolClass)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .where(Section.school_id == ctx.school_id, Section.academic_year_id == exam.academic_year_id)
        .order_by(SchoolClass.sort_order, Section.name)
    ).all()
    return {s.id: (s, c) for s, c in rows}


def summary(ctx: Ctx, exam_id: uuid.UUID) -> DashboardSummary:
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    bands = load_bands(ctx.db, ctx.school_id, exam.grade_scale_id)
    students = (
        ctx.db.scalar(
            select(func.count())
            .select_from(StudentEnrolment)
            .join(Student, Student.id == StudentEnrolment.student_id)
            .where(
                StudentEnrolment.school_id == ctx.school_id,
                StudentEnrolment.academic_year_id == exam.academic_year_id,
                Student.deleted_at.is_(None),
            )
        )
        or 0
    )
    rows = ctx.db.execute(
        select(V.percentage, V.passed).where(V.school_id == ctx.school_id, V.exam_id == exam.id)
    ).all()
    pcts = [r.percentage for r in rows if r.percentage is not None]
    grades = Counter(grade_for(p, bands) or "-" for p in pcts)
    order = [b.grade for b in sorted(bands, key=lambda b: b.min_percent, reverse=True)]
    distribution = [GradeCount(grade=g, count=grades.get(g, 0)) for g in order]
    secs = _sections(ctx, exam)
    published = (
        ctx.db.scalar(
            select(func.count())
            .select_from(ResultPublication)
            .where(ResultPublication.exam_id == exam.id, ResultPublication.school_id == ctx.school_id)
        )
        or 0
    )
    return DashboardSummary(
        exam_id=exam.id,
        exam_name=exam.name,
        students=int(students),
        students_with_results=len(rows),
        average_percent=round2(sum(pcts) / len(pcts)) if pcts else None,
        pass_percent=_pct(sum(1 for r in rows if r.passed), len(rows)),
        grade_distribution=distribution,
        sections_published=int(published),
        sections_total=len(secs),
    )


def sections(ctx: Ctx, exam_id: uuid.UUID, class_id: uuid.UUID | None = None) -> list[SectionPerformance]:
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    agg = {
        r.section_id: r
        for r in ctx.db.execute(
            select(
                V.section_id,
                func.count().label("n"),
                func.avg(V.percentage).label("avg"),
                func.sum(case((V.passed, 1), else_=0)).label("passed"),
            )
            .where(V.school_id == ctx.school_id, V.exam_id == exam.id)
            .group_by(V.section_id)
        ).all()
    }
    published = set(
        ctx.db.scalars(
            select(ResultPublication.section_id).where(
                ResultPublication.exam_id == exam.id, ResultPublication.school_id == ctx.school_id
            )
        )
    )
    out = []
    for sid, (s, c) in _sections(ctx, exam).items():
        if class_id and c.id != class_id:
            continue
        a = agg.get(sid)
        out.append(
            SectionPerformance(
                section_id=sid,
                section_name=section_label(c.name, s.name),
                class_id=c.id,
                class_name=c.name,
                students=int(a.n) if a else 0,
                average_percent=_avg(a.avg) if a else None,
                pass_percent=_pct(a.passed, a.n) if a else None,
                published=sid in published,
            )
        )
    return out


def subjects(
    ctx: Ctx, exam_id: uuid.UUID, class_id: uuid.UUID | None = None, section_id: uuid.UUID | None = None
) -> list[SubjectPerformance]:
    """Average % per subject, weakest first."""
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    pass_percent = ctx.db.scalar(select(School.pass_percent).where(School.id == ctx.school_id)) or Decimal(33)
    obtained = func.coalesce(Mark.marks_obtained, 0)
    pass_marks = func.coalesce(ExamSubject.pass_marks, ExamSubject.max_marks * pass_percent / 100)
    stmt = (
        select(
            Subject.id,
            Subject.name,
            func.count().label("n"),
            func.avg(obtained * 100 / ExamSubject.max_marks).label("avg"),
            func.sum(case((obtained >= pass_marks, 1), else_=0)).label("passed"),
        )
        .join(ExamSubject, ExamSubject.id == Mark.exam_subject_id)
        .join(Subject, Subject.id == ExamSubject.subject_id)
        .where(Mark.school_id == ctx.school_id, ExamSubject.exam_id == exam.id, Mark.status != MarkStatus.EXEMPT)
        .group_by(Subject.id, Subject.name)
    )
    if class_id:
        stmt = stmt.where(ExamSubject.class_id == class_id)
    if section_id:
        stmt = stmt.where(Mark.section_id == section_id)
    rows = [
        SubjectPerformance(
            subject_id=r.id,
            subject_name=r.name,
            students=int(r.n),
            average_percent=_avg(r.avg),
            pass_percent=_pct(r.passed, r.n),
        )
        for r in ctx.db.execute(stmt).all()
    ]
    return sorted(rows, key=lambda r: (r.average_percent is None, r.average_percent or 0))


def _student_info(ctx: Ctx, ids: set[uuid.UUID]) -> dict[uuid.UUID, Student]:
    if not ids:
        return {}
    return {
        s.id: s for s in ctx.db.scalars(select(Student).where(Student.school_id == ctx.school_id, Student.id.in_(ids)))
    }


def attention(ctx: Ctx, exam_id: uuid.UUID, section_id: uuid.UUID | None = None) -> list[AttentionStudent]:
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    current_stmt = select(results_view).where(V.school_id == ctx.school_id, V.exam_id == exam.id)
    if section_id:
        current_stmt = current_stmt.where(V.section_id == section_id)
    current = ctx.db.execute(current_stmt).all()

    # Previous result per student: the latest earlier exam in the same year.
    prev: dict[uuid.UUID, Decimal | None] = {}
    for r in ctx.db.execute(
        select(V.student_id, V.percentage, Exam.sequence)
        .join(Exam, Exam.id == V.exam_id)
        .where(
            V.school_id == ctx.school_id, Exam.academic_year_id == exam.academic_year_id, Exam.sequence < exam.sequence
        )
        .order_by(Exam.sequence)
    ).all():
        prev[r.student_id] = r.percentage

    secs = _sections(ctx, exam)
    flagged = []
    for r in current:
        reasons = []
        if r.subjects_failed >= ATTENTION_FAILS:
            reasons.append(f"Below pass mark in {r.subjects_failed} subjects")
        p = prev.get(r.student_id)
        drop = round2(p - r.percentage) if p is not None and r.percentage is not None else None
        if drop is not None and drop >= ATTENTION_DROP:
            reasons.append(f"Dropped {drop} points since the last exam")
        if reasons:
            flagged.append((r, p, drop, reasons))
    info = _student_info(ctx, {f[0].student_id for f in flagged})
    out = []
    for r, p, drop, reasons in flagged:
        s = info.get(r.student_id)
        sec = secs.get(r.section_id)
        if s is None or s.deleted_at is not None:
            continue
        out.append(
            AttentionStudent(
                student_id=s.id,
                full_name=s.full_name,
                admission_no=s.admission_no,
                section_id=r.section_id,
                section_name=section_label(sec[1].name, sec[0].name) if sec else "",
                percentage=_avg(r.percentage),
                previous_percentage=_avg(p),
                drop=drop,
                subjects_failed=int(r.subjects_failed),
                reasons=reasons,
            )
        )
    return sorted(out, key=lambda a: (-a.subjects_failed, -(a.drop or 0), a.full_name))


def toppers(ctx: Ctx, exam_id: uuid.UUID, section_id: uuid.UUID | None = None, top: int = 3) -> list[Topper]:
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    bands = load_bands(ctx.db, ctx.school_id, exam.grade_scale_id)
    stmt = select(results_view).where(
        V.school_id == ctx.school_id, V.exam_id == exam.id, V.section_rank <= top, V.percentage.is_not(None)
    )
    if section_id:
        stmt = stmt.where(V.section_id == section_id)
    rows = ctx.db.execute(stmt.order_by(V.section_id, V.section_rank)).all()
    info = _student_info(ctx, {r.student_id for r in rows})
    secs = _sections(ctx, exam)
    out = []
    for r in rows:
        s, sec = info.get(r.student_id), secs.get(r.section_id)
        if s is None or sec is None or s.deleted_at is not None:
            continue
        out.append(
            Topper(
                section_id=r.section_id,
                section_name=section_label(sec[1].name, sec[0].name),
                student_id=s.id,
                full_name=s.full_name,
                admission_no=s.admission_no,
                percentage=_avg(r.percentage),
                grade=grade_for(r.percentage, bands),
                rank=int(r.section_rank),
            )
        )
    order = {sid: i for i, sid in enumerate(secs)}
    return sorted(out, key=lambda t: (order.get(t.section_id, 0), t.rank, t.full_name))


def section_students(ctx: Ctx, exam_id: uuid.UUID, section_id: uuid.UUID) -> list[SectionStudentResult]:
    """Drill-down: every student in a section with their result for the exam."""
    exam = get_owned(ctx, Exam, exam_id, "Exam")
    ensure_section_in_school(ctx, section_id)
    bands = load_bands(ctx.db, ctx.school_id, exam.grade_scale_id)
    res = {
        r.student_id: r
        for r in ctx.db.execute(
            select(results_view).where(V.school_id == ctx.school_id, V.exam_id == exam.id, V.section_id == section_id)
        ).all()
    }
    out = []
    for s, e in ctx.db.execute(
        select(Student, StudentEnrolment)
        .join(StudentEnrolment, StudentEnrolment.student_id == Student.id)
        .where(
            StudentEnrolment.section_id == section_id,
            StudentEnrolment.school_id == ctx.school_id,
            Student.deleted_at.is_(None),
        )
    ).all():
        r = res.get(s.id)
        out.append(
            SectionStudentResult(
                student_id=s.id,
                full_name=s.full_name,
                admission_no=s.admission_no,
                roll_no=e.roll_no,
                total_obtained=_avg(r.total_obtained) if r else None,
                total_max=_avg(r.total_max) if r else None,
                percentage=_avg(r.percentage) if r else None,
                grade=grade_for(r.percentage, bands) if r else None,
                rank=int(r.section_rank) if r else None,
                subjects_failed=int(r.subjects_failed) if r else None,
                passed=bool(r.passed) if r else None,
            )
        )
    return sorted(out, key=lambda x: (x.rank is None, x.rank or 0, x.full_name))


def grouped_by(items: list[Any], key: str) -> dict[Any, list[Any]]:
    groups: dict[Any, list[Any]] = defaultdict(list)
    for i in items:
        groups[getattr(i, key)].append(i)
    return groups
