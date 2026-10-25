"""School profile, logo, staff, audit log (school-scoped) and public school endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile

from app.core.deps import AdminCtx, AnySchoolCtx, DbDep, ManagerCtx
from app.core.errors import NotFound
from app.schemas.common import Ok
from app.schemas.setup import (
    AuditOut,
    DemoRequestIn,
    PublicSchool,
    SchoolOut,
    SchoolUpdate,
    StaffCreate,
    StaffOut,
)
from app.schemas.website import ImageUploaded, PublicWebsite, WebsiteContent
from app.services import audit, schools, website

router = APIRouter(tags=["school"])
public = APIRouter(prefix="/public", tags=["public"])


@router.get("/school", response_model=SchoolOut)
def get_school(ctx: AnySchoolCtx) -> SchoolOut:
    return SchoolOut.model_validate(schools.get_own_school(ctx))


@router.patch("/school", response_model=SchoolOut)
def update_school(body: SchoolUpdate, ctx: AdminCtx) -> SchoolOut:
    return SchoolOut.model_validate(schools.update_own_school(ctx, body))


@router.post("/school/logo", response_model=SchoolOut)
async def upload_logo(ctx: AdminCtx, file: Annotated[UploadFile, File()]) -> SchoolOut:
    content = await file.read(1024 * 1024 + 1)
    return SchoolOut.model_validate(schools.upload_logo(ctx, content, file.content_type or ""))


@router.get("/school/logo", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def get_logo(ctx: AnySchoolCtx) -> Response:
    logo = schools.logo_bytes(schools.get_own_school(ctx))
    if logo is None:
        raise NotFound("Logo")
    return Response(logo[0], media_type=logo[1], headers={"Cache-Control": "private, max-age=3600"})


@router.get("/staff", response_model=list[StaffOut])
def list_staff(ctx: ManagerCtx) -> list[StaffOut]:
    return schools.list_staff(ctx, ctx.school_id)


@router.post("/staff", response_model=StaffOut, status_code=201)
def add_staff(body: StaffCreate, ctx: AdminCtx) -> StaffOut:
    return schools.add_staff(ctx, ctx.school_id, body)


@router.delete("/staff/{role_id}", response_model=Ok)
def remove_staff(role_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    schools.deactivate_staff(ctx, ctx.school_id, role_id)
    return Ok()


@router.get("/audit-logs", response_model=list[AuditOut])
def audit_logs(
    ctx: ManagerCtx, entity_id: uuid.UUID | None = None, limit: Annotated[int, Query(ge=1, le=500)] = 100
) -> list[AuditOut]:
    return [AuditOut.model_validate(r) for r in audit.list_logs(ctx, entity_id, limit)]


# ----------------------------------------------------------------- public
@public.get("/schools/{code}", response_model=PublicSchool)
def public_school(code: str, db: DbDep) -> PublicSchool:
    return schools.to_public(schools.public_school(db, code))


@public.get("/schools/{code}/logo", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def public_logo(code: str, db: DbDep) -> Response:
    logo = schools.logo_bytes(schools.public_school(db, code))
    if logo is None:
        raise NotFound("Logo")
    return Response(logo[0], media_type=logo[1], headers={"Cache-Control": "public, max-age=86400"})


@public.post("/demo-requests", response_model=Ok, status_code=201)
def demo_request(body: DemoRequestIn, db: DbDep) -> Ok:
    schools.create_demo_request(db, body)
    return Ok()


# ----------------------------------------------------------------- website
@router.get("/school/website", response_model=WebsiteContent, tags=["website"])
def get_website(ctx: ManagerCtx) -> WebsiteContent:
    return website.get_content(ctx)


@router.put("/school/website", response_model=WebsiteContent, tags=["website"])
def put_website(body: WebsiteContent, ctx: AdminCtx) -> WebsiteContent:
    return website.save_content(ctx, body)


@router.post("/school/website/images", response_model=ImageUploaded, status_code=201, tags=["website"])
async def upload_website_image(ctx: AdminCtx, file: Annotated[UploadFile, File()]) -> ImageUploaded:
    content = await file.read(website.MAX_IMAGE_BYTES + 1)
    return ImageUploaded(image_id=website.upload_image(ctx, content, file.content_type or ""))


@public.get("/schools/{code}/website", response_model=PublicWebsite, tags=["website"])
def public_website(code: str, db: DbDep) -> PublicWebsite:
    return website.public_website(db, code)


@public.get(
    "/schools/{code}/images/{image_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
    tags=["website"],
)
def public_image(code: str, image_id: str, db: DbDep) -> Response:
    data, mime = website.public_image(db, code, image_id)
    return Response(data, media_type=mime, headers={"Cache-Control": "public, max-age=604800, immutable"})
