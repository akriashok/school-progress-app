"""Report card PDF (DESIGN.md §10): Jinja2 HTML -> WeasyPrint, cached by marks version."""

import base64
import hashlib
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select

from app.core.deps import Ctx
from app.core.errors import AppError
from app.models import AcademicYear, Exam, ExamSubject, Mark, School, SchoolClass, Section, StudentEnrolment
from app.services import audit, results
from app.services.academics import section_label
from app.services.permissions import ensure_student_visible
from app.services.schools import logo_bytes
from app.services.storage import get_storage

_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def _num(v: Any) -> str:
    if v is None:
        return "-"
    d = Decimal(str(v)).quantize(Decimal("0.01"))
    return f"{d.normalize():f}" if d == d.to_integral() else f"{d:f}"


_env.filters["num"] = _num


def _marks_version(ctx: Ctx, student_id: uuid.UUID, exam_id: uuid.UUID) -> str:
    row = ctx.db.execute(
        select(func.count(), func.coalesce(func.sum(Mark.version), 0), func.max(Mark.updated_at))
        .join(ExamSubject, ExamSubject.id == Mark.exam_subject_id)
        .where(Mark.school_id == ctx.school_id, Mark.student_id == student_id, ExamSubject.exam_id == exam_id)
    ).one()
    school = ctx.db.get(School, ctx.school_id)
    raw = f"{row[0]}:{row[1]}:{row[2]}:{school.updated_at if school else ''}:v1"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def render_html(ctx: Ctx, student_id: uuid.UUID, exam_id: uuid.UUID) -> str:
    student = ensure_student_visible(ctx, student_id)
    result = results.student_exam_result(ctx, student_id, exam_id)  # enforces published-only for families
    school = ctx.db.get(School, ctx.school_id)
    exam = ctx.db.get(Exam, exam_id)
    assert school is not None and exam is not None
    year = ctx.db.get(AcademicYear, exam.academic_year_id)
    sec_row = ctx.db.execute(
        select(Section, SchoolClass, StudentEnrolment.roll_no)
        .join(SchoolClass, SchoolClass.id == Section.class_id)
        .join(StudentEnrolment, StudentEnrolment.section_id == Section.id)
        .where(Section.id == result.section_id, StudentEnrolment.student_id == student_id)
    ).first()
    logo = logo_bytes(school)
    logo_uri = f"data:{logo[1]};base64,{base64.b64encode(logo[0]).decode()}" if logo else None
    return _env.get_template("report_card.html").render(
        school=school,
        student=student,
        result=result,
        year_name=year.name if year else "",
        section_name=section_label(sec_row[1].name, sec_row[0].name) if sec_row else "",
        roll_no=sec_row[2] if sec_row else None,
        logo_data_uri=logo_uri,
        generated_on=date.today().strftime("%d %b %Y"),
    )


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # OSError: missing Pango/GTK libraries
        raise AppError(
            "PDF generation is not available on this server", code="PDF_UNAVAILABLE", status_code=503
        ) from exc
    pdf: bytes = HTML(string=html).write_pdf()
    return pdf


def report_card(ctx: Ctx, student_id: uuid.UUID, exam_id: uuid.UUID) -> bytes:
    html = render_html(ctx, student_id, exam_id)  # permission + visibility checks happen here
    key = f"report-cards/{ctx.school_id}/{student_id}/{exam_id}/{_marks_version(ctx, student_id, exam_id)}.pdf"
    storage = get_storage()
    pdf = storage.get(key)
    if pdf is None:
        pdf = html_to_pdf(html)
        storage.put(key, pdf, "application/pdf")
    audit.record(
        ctx, audit.Action.REPORT_CARD_DOWNLOAD, entity="student", entity_id=student_id, new={"exam_id": exam_id}
    )
    return pdf
