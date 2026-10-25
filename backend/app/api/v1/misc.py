"""Consent, device registration and platform-admin endpoints."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Request
from pydantic import BaseModel, Field

from app.core.deps import AnySchoolCtx, CtxDep, ParentCtx, PlatformCtx
from app.core.errors import NotFound
from app.schemas.common import Ok
from app.schemas.setup import SchoolCreate, SchoolOut, StaffCreate, StaffOut
from app.services import consent, notifications, schools

router = APIRouter()


class ConsentOut(BaseModel):
    version: int
    body: str
    accepted: bool


class DeviceIn(BaseModel):
    fcm_token: str = Field(min_length=10, max_length=4096)
    platform: Literal["android", "ios", "web"] = "android"


class DeviceOut(BaseModel):
    id: uuid.UUID


@router.get("/consent/current", response_model=ConsentOut, tags=["consent"])
def consent_current(ctx: ParentCtx) -> ConsentOut:
    text = consent.current_text(ctx)
    if text is None:
        raise NotFound("Consent text")
    return ConsentOut(version=text.version, body=text.body, accepted=consent.has_accepted(ctx, text))


@router.post("/consent/accept", response_model=Ok, tags=["consent"])
def consent_accept(ctx: ParentCtx, request: Request, version: Annotated[int, Body(embed=True)]) -> Ok:
    consent.accept(ctx, version, request.headers.get("user-agent"))
    return Ok()


@router.post("/devices", response_model=DeviceOut, status_code=201, tags=["notifications"])
def register_device(body: DeviceIn, ctx: AnySchoolCtx) -> DeviceOut:
    return DeviceOut(id=notifications.register_device(ctx.db, ctx.user, body.fcm_token, body.platform).id)


@router.delete("/devices/{device_id}", response_model=Ok, tags=["notifications"])
def delete_device(device_id: uuid.UUID, ctx: CtxDep) -> Ok:
    notifications.delete_device(ctx.db, ctx.user, device_id)
    return Ok()


# ---------------------------------------------------------- platform admin
admin = APIRouter(prefix="/admin", tags=["platform-admin"])


@admin.get("/schools", response_model=list[SchoolOut])
def list_schools(ctx: PlatformCtx) -> list[SchoolOut]:
    return [SchoolOut.model_validate(s) for s in schools.list_schools(ctx)]


@admin.post(
    "/schools",
    response_model=SchoolOut,
    status_code=201,
    summary="Create a school (with default CBSE grade scale and consent text)",
)
def create_school(body: SchoolCreate, ctx: PlatformCtx) -> SchoolOut:
    return SchoolOut.model_validate(schools.create_school(ctx, body))


@admin.get("/schools/{school_id}", response_model=SchoolOut)
def get_school(school_id: uuid.UUID, ctx: PlatformCtx) -> SchoolOut:
    return SchoolOut.model_validate(schools.get_school_admin(ctx, school_id))


@admin.patch("/schools/{school_id}", response_model=SchoolOut, summary="Activate or deactivate a school")
def set_active(school_id: uuid.UUID, ctx: PlatformCtx, is_active: Annotated[bool, Body(embed=True)]) -> SchoolOut:
    return SchoolOut.model_validate(schools.set_school_active(ctx, school_id, is_active))


@admin.get("/schools/{school_id}/admins", response_model=list[StaffOut])
def list_admins(school_id: uuid.UUID, ctx: PlatformCtx) -> list[StaffOut]:
    schools.get_school_admin(ctx, school_id)
    return schools.list_staff(ctx, school_id)


@admin.post(
    "/schools/{school_id}/admins",
    response_model=StaffOut,
    status_code=201,
    summary="Create or re-activate a school admin / principal login",
)
def add_admin(school_id: uuid.UUID, body: StaffCreate, ctx: PlatformCtx) -> StaffOut:
    schools.get_school_admin(ctx, school_id)
    return schools.add_staff(ctx, school_id, body)
