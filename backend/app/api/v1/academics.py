import uuid

from fastapi import APIRouter

from app.core.deps import AdminCtx, ManagerCtx, StaffCtx
from app.schemas.common import Ok
from app.schemas.setup import (
    AcademicYearIn,
    AcademicYearOut,
    ClassIn,
    ClassOut,
    GradeScaleIn,
    GradeScaleOut,
    SectionIn,
    SectionOut,
    SectionSubjectsIn,
    SectionUpdate,
    SubjectIn,
    SubjectOut,
)
from app.services import academics as svc
from app.services.permissions import ensure_can_view_section

router = APIRouter(tags=["academics"])


# --------------------------------------------------------- academic years
@router.get("/academic-years", response_model=list[AcademicYearOut])
def list_years(ctx: StaffCtx) -> list[AcademicYearOut]:
    return [AcademicYearOut.model_validate(y) for y in svc.list_years(ctx)]


@router.post("/academic-years", response_model=AcademicYearOut, status_code=201)
def create_year(body: AcademicYearIn, ctx: AdminCtx) -> AcademicYearOut:
    return AcademicYearOut.model_validate(svc.create_year(ctx, body))


@router.put("/academic-years/{year_id}", response_model=AcademicYearOut)
def update_year(year_id: uuid.UUID, body: AcademicYearIn, ctx: AdminCtx) -> AcademicYearOut:
    return AcademicYearOut.model_validate(svc.update_year(ctx, year_id, body))


@router.delete("/academic-years/{year_id}", response_model=Ok)
def delete_year(year_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_year(ctx, year_id)
    return Ok()


# ----------------------------------------------------------------- classes
@router.get("/classes", response_model=list[ClassOut])
def list_classes(ctx: StaffCtx) -> list[ClassOut]:
    return [ClassOut.model_validate(c) for c in svc.list_classes(ctx)]


@router.post("/classes", response_model=ClassOut, status_code=201)
def create_class(body: ClassIn, ctx: AdminCtx) -> ClassOut:
    return ClassOut.model_validate(svc.create_class(ctx, body))


@router.put("/classes/{class_id}", response_model=ClassOut)
def update_class(class_id: uuid.UUID, body: ClassIn, ctx: AdminCtx) -> ClassOut:
    return ClassOut.model_validate(svc.update_class(ctx, class_id, body))


@router.delete("/classes/{class_id}", response_model=Ok)
def delete_class(class_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_class(ctx, class_id)
    return Ok()


# ---------------------------------------------------------------- subjects
@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(ctx: StaffCtx) -> list[SubjectOut]:
    return [SubjectOut.model_validate(s) for s in svc.list_subjects(ctx)]


@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(body: SubjectIn, ctx: AdminCtx) -> SubjectOut:
    return SubjectOut.model_validate(svc.create_subject(ctx, body))


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: uuid.UUID, body: SubjectIn, ctx: AdminCtx) -> SubjectOut:
    return SubjectOut.model_validate(svc.update_subject(ctx, subject_id, body))


@router.delete("/subjects/{subject_id}", response_model=Ok)
def delete_subject(subject_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_subject(ctx, subject_id)
    return Ok()


# ---------------------------------------------------------------- sections
@router.get("/sections", response_model=list[SectionOut])
def list_sections(
    ctx: ManagerCtx, academic_year_id: uuid.UUID | None = None, class_id: uuid.UUID | None = None
) -> list[SectionOut]:
    return svc.section_rows(ctx, academic_year_id=academic_year_id, class_id=class_id)


@router.post("/sections", response_model=SectionOut, status_code=201)
def create_section(body: SectionIn, ctx: AdminCtx) -> SectionOut:
    return svc.create_section(ctx, body)


@router.get("/sections/{section_id}", response_model=SectionOut)
def get_section(section_id: uuid.UUID, ctx: StaffCtx) -> SectionOut:
    ensure_can_view_section(ctx, section_id)
    return svc.get_section_out(ctx, section_id)


@router.patch("/sections/{section_id}", response_model=SectionOut)
def update_section(section_id: uuid.UUID, body: SectionUpdate, ctx: AdminCtx) -> SectionOut:
    return svc.update_section(ctx, section_id, body)


@router.delete("/sections/{section_id}", response_model=Ok)
def delete_section(section_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_section(ctx, section_id)
    return Ok()


@router.get("/sections/{section_id}/subjects", response_model=list[SubjectOut])
def get_section_subjects(section_id: uuid.UUID, ctx: StaffCtx) -> list[SubjectOut]:
    ensure_can_view_section(ctx, section_id)
    return [SubjectOut.model_validate(s) for s in svc.section_subjects(ctx, section_id)]


@router.put("/sections/{section_id}/subjects", response_model=list[SubjectOut])
def put_section_subjects(section_id: uuid.UUID, body: SectionSubjectsIn, ctx: AdminCtx) -> list[SubjectOut]:
    return [SubjectOut.model_validate(s) for s in svc.set_section_subjects(ctx, section_id, body.subject_ids)]


# ------------------------------------------------------------ grade scales
@router.get("/grade-scales", response_model=list[GradeScaleOut])
def list_scales(ctx: ManagerCtx) -> list[GradeScaleOut]:
    return svc.list_scales(ctx)


@router.post("/grade-scales", response_model=GradeScaleOut, status_code=201)
def create_scale(body: GradeScaleIn, ctx: AdminCtx) -> GradeScaleOut:
    return svc.create_scale(ctx, body)


@router.put("/grade-scales/{scale_id}", response_model=GradeScaleOut)
def update_scale(scale_id: uuid.UUID, body: GradeScaleIn, ctx: AdminCtx) -> GradeScaleOut:
    return svc.update_scale(ctx, scale_id, body)


@router.delete("/grade-scales/{scale_id}", response_model=Ok)
def delete_scale(scale_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_scale(ctx, scale_id)
    return Ok()
