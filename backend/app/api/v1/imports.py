import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Body, File, Response, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import StaffCtx
from app.core.errors import Forbidden
from app.models import Import, ImportStatus, ImportType, RoleType
from app.services import excel, imports

router = APIRouter(prefix="/imports", tags=["imports"])

TemplateType = Literal["students", "teachers", "marks"]


class ImportOut(BaseModel):
    id: uuid.UUID
    type: ImportType
    status: ImportStatus
    filename: str | None
    total_rows: int | None
    valid_rows: int | None
    error_count: int
    errors: list[dict[str, Any]]
    preview: list[dict[str, Any]]
    result: dict[str, Any] | None
    created_at: datetime
    committed_at: datetime | None


def _out(imp: Import) -> ImportOut:
    ctx = imp.context or {}
    return ImportOut(
        id=imp.id,
        type=imp.type,
        status=imp.status,
        filename=ctx.get("filename"),
        total_rows=imp.total_rows,
        valid_rows=imp.valid_rows,
        error_count=len(imp.errors or []),
        errors=imp.errors or [],
        preview=ctx.get("preview", []),
        result=ctx.get("result"),
        created_at=imp.created_at,
        committed_at=imp.committed_at,
    )


def _xlsx(data: bytes, filename: str) -> Response:
    return Response(
        data, media_type=excel.XLSX_MIME, headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/templates/{type}", response_class=Response, responses={200: {"content": {excel.XLSX_MIME: {}}}})
def template(
    type: TemplateType, ctx: StaffCtx, exam_subject_id: uuid.UUID | None = None, section_id: uuid.UUID | None = None
) -> Response:
    if type == "marks":
        if exam_subject_id is None or section_id is None:
            from app.core.errors import ValidationFailed

            raise ValidationFailed("exam_subject_id and section_id are required")
        data, name = imports.marks_template(ctx, exam_subject_id, section_id)
        return _xlsx(data, name)
    if ctx.user.role != RoleType.SCHOOL_ADMIN:
        raise Forbidden()
    return _xlsx(
        excel.students_template() if type == "students" else excel.teachers_template(), f"{type}_template.xlsx"
    )


@router.get("", response_model=list[ImportOut])
def list_imports(ctx: StaffCtx) -> list[ImportOut]:
    return [_out(i) for i in imports.list_imports(ctx)]


@router.post(
    "/{type}", response_model=ImportOut, status_code=202, summary="Upload a file; validation runs in the background"
)
async def upload(
    type: TemplateType,
    ctx: StaffCtx,
    tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    exam_subject_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
) -> ImportOut:
    limit = get_settings().max_upload_mb * 1024 * 1024
    content = await file.read(limit + 1)
    imp = imports.create_import(
        ctx, ImportType(type.upper()), file.filename or "upload.xlsx", content, exam_subject_id, section_id
    )
    tasks.add_task(imports.validate_in_background, imp.id, ctx.user)
    return _out(imp)


@router.get("/{import_id}", response_model=ImportOut)
def get_import(import_id: uuid.UUID, ctx: StaffCtx) -> ImportOut:
    return _out(imports.get_import(ctx, import_id))


@router.get(
    "/{import_id}/errors.xlsx",
    response_class=Response,
    responses={200: {"content": {excel.XLSX_MIME: {}}}},
    summary="Download row errors",
)
def import_errors(import_id: uuid.UUID, ctx: StaffCtx) -> Response:
    imp = imports.get_import(ctx, import_id)
    data = excel.export_table(
        "Errors", [("row", "Row"), ("column", "Column"), ("message", "Problem")], imp.errors or []
    )
    return _xlsx(data, f"import_errors_{import_id}.xlsx")


@router.post("/{import_id}/commit", response_model=ImportOut, summary="Save all valid rows in one transaction")
def commit(
    import_id: uuid.UUID, ctx: StaffCtx, reason: Annotated[str | None, Body(embed=True, max_length=500)] = None
) -> ImportOut:
    return _out(imports.commit(ctx, import_id, reason))
