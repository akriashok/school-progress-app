import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from app.core.deps import AnySchoolCtx, Ctx, ManagerCtx, ParentCtx
from app.schemas.exams import (
    AttentionStudent,
    ChildOut,
    DashboardSummary,
    ExamResultDetail,
    ExamResultSummary,
    Progress,
    SectionPerformance,
    SectionStudentResult,
    SubjectPerformance,
    Topper,
)
from app.services import audit, consent, dashboard, excel, pdf, results

router = APIRouter(tags=["results"])
dash = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _family_gate(ctx: Ctx) -> None:
    consent.require_consent(ctx)


@router.get("/children", response_model=list[ChildOut])
def children(ctx: ParentCtx) -> list[ChildOut]:
    _family_gate(ctx)
    return results.children(ctx)


@router.get("/students/{student_id}/results", response_model=list[ExamResultSummary])
def student_results(
    student_id: uuid.UUID, ctx: AnySchoolCtx, academic_year_id: uuid.UUID | None = None
) -> list[ExamResultSummary]:
    _family_gate(ctx)
    return results.student_results(ctx, student_id, academic_year_id)


@router.get("/students/{student_id}/results/{exam_id}", response_model=ExamResultDetail)
def student_exam_result(student_id: uuid.UUID, exam_id: uuid.UUID, ctx: AnySchoolCtx) -> ExamResultDetail:
    _family_gate(ctx)
    return results.student_exam_result(ctx, student_id, exam_id)


@router.get("/students/{student_id}/progress", response_model=Progress)
def student_progress(student_id: uuid.UUID, ctx: AnySchoolCtx, academic_year_id: uuid.UUID | None = None) -> Progress:
    _family_gate(ctx)
    return results.student_progress(ctx, student_id, academic_year_id)


@router.get(
    "/students/{student_id}/report-cards/{exam_id}.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def report_card(student_id: uuid.UUID, exam_id: uuid.UUID, ctx: AnySchoolCtx) -> Response:
    _family_gate(ctx)
    data = pdf.report_card(ctx, student_id, exam_id)
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="report-card-{exam_id}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


# --------------------------------------------------------------- dashboard
@dash.get("/summary", response_model=DashboardSummary)
def summary(exam_id: uuid.UUID, ctx: ManagerCtx) -> DashboardSummary:
    return dashboard.summary(ctx, exam_id)


@dash.get("/sections", response_model=list[SectionPerformance])
def sections(exam_id: uuid.UUID, ctx: ManagerCtx, class_id: uuid.UUID | None = None) -> list[SectionPerformance]:
    return dashboard.sections(ctx, exam_id, class_id)


@dash.get("/subjects", response_model=list[SubjectPerformance], summary="Weakest subjects first")
def subjects(
    exam_id: uuid.UUID, ctx: ManagerCtx, class_id: uuid.UUID | None = None, section_id: uuid.UUID | None = None
) -> list[SubjectPerformance]:
    return dashboard.subjects(ctx, exam_id, class_id, section_id)


@dash.get("/attention", response_model=list[AttentionStudent])
def attention(exam_id: uuid.UUID, ctx: ManagerCtx, section_id: uuid.UUID | None = None) -> list[AttentionStudent]:
    return dashboard.attention(ctx, exam_id, section_id)


@dash.get("/toppers", response_model=list[Topper])
def toppers(
    exam_id: uuid.UUID,
    ctx: ManagerCtx,
    section_id: uuid.UUID | None = None,
    top: Annotated[int, Query(ge=1, le=20)] = 3,
) -> list[Topper]:
    return dashboard.toppers(ctx, exam_id, section_id, top)


@dash.get("/students", response_model=list[SectionStudentResult], summary="Drill-down: a section's results")
def section_students(exam_id: uuid.UUID, section_id: uuid.UUID, ctx: ManagerCtx) -> list[SectionStudentResult]:
    return dashboard.section_students(ctx, exam_id, section_id)


ReportName = Literal["summary", "sections", "subjects", "attention", "toppers", "students"]

_EXPORT_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "sections": [
        ("section_name", "Section"),
        ("students", "Students"),
        ("average_percent", "Average %"),
        ("pass_percent", "Pass %"),
        ("published", "Published"),
    ],
    "subjects": [
        ("subject_name", "Subject"),
        ("students", "Students"),
        ("average_percent", "Average %"),
        ("pass_percent", "Pass %"),
    ],
    "attention": [
        ("admission_no", "Admission no"),
        ("full_name", "Student"),
        ("section_name", "Section"),
        ("percentage", "%"),
        ("previous_percentage", "Previous %"),
        ("drop", "Drop"),
        ("subjects_failed", "Subjects failed"),
        ("reasons", "Reasons"),
    ],
    "toppers": [
        ("section_name", "Section"),
        ("rank", "Rank"),
        ("admission_no", "Admission no"),
        ("full_name", "Student"),
        ("percentage", "%"),
        ("grade", "Grade"),
    ],
    "students": [
        ("roll_no", "Roll no"),
        ("admission_no", "Admission no"),
        ("full_name", "Student"),
        ("total_obtained", "Total"),
        ("total_max", "Max"),
        ("percentage", "%"),
        ("grade", "Grade"),
        ("rank", "Rank"),
        ("subjects_failed", "Subjects failed"),
    ],
    "summary": [("grade", "Grade"), ("count", "Students")],
}


@dash.get(
    "/export",
    response_class=Response,
    responses={200: {"content": {excel.XLSX_MIME: {}}}},
    summary="Download a dashboard table as .xlsx",
)
def export(
    report: ReportName,
    exam_id: uuid.UUID,
    ctx: ManagerCtx,
    class_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
) -> Response:
    rows: list[dict[str, object]]
    if report == "sections":
        rows = [r.model_dump() for r in dashboard.sections(ctx, exam_id, class_id)]
    elif report == "subjects":
        rows = [r.model_dump() for r in dashboard.subjects(ctx, exam_id, class_id, section_id)]
    elif report == "attention":
        rows = [r.model_dump() for r in dashboard.attention(ctx, exam_id, section_id)]
    elif report == "toppers":
        rows = [r.model_dump() for r in dashboard.toppers(ctx, exam_id, section_id)]
    elif report == "students":
        if section_id is None:
            from app.core.errors import ValidationFailed

            raise ValidationFailed("section_id is required for the students report")
        rows = [r.model_dump() for r in dashboard.section_students(ctx, exam_id, section_id)]
    else:
        rows = [g.model_dump() for g in dashboard.summary(ctx, exam_id).grade_distribution]
    data = excel.export_table(report.capitalize(), _EXPORT_COLUMNS[report], rows)
    audit.record(
        ctx, audit.Action.EXPORT, entity="dashboard", new={"report": report, "exam_id": exam_id, "rows": len(rows)}
    )
    return Response(
        data, media_type=excel.XLSX_MIME, headers={"Content-Disposition": f'attachment; filename="{report}.xlsx"'}
    )
