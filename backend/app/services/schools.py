"""Schools: platform-admin onboarding, school profile, staff roles, public page."""

import uuid

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.db import set_tenant
from app.core.deps import Ctx
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.models import ConsentText, RoleType, School, User, UserRole
from app.models.entities import DemoRequest
from app.schemas.setup import (
    DemoRequestIn,
    PublicSchool,
    SchoolCreate,
    SchoolUpdate,
    StaffCreate,
    StaffOut,
)
from app.services import audit, grading
from app.services.storage import get_storage
from app.services.users import ensure_role, get_or_create_user

DEFAULT_CONSENT = (
    "We, the school, use this app to share your child's marks, report cards and progress with you. "
    "We collect your name, phone number and your child's academic records only for this purpose. "
    "Data is stored in India, is never sold, and is not shared with advertisers. "
    "You can ask the school to correct or delete your data at any time."
)

ALLOWED_LOGO_TYPES = {"image/png": "png", "image/jpeg": "jpg"}


# ------------------------------------------------------ platform admin
def list_schools(ctx: Ctx) -> list[School]:
    audit.record(ctx, audit.Action.PLATFORM_ADMIN_ACCESS, entity="schools")
    return list(ctx.db.scalars(select(School).order_by(School.name)))


def create_school(ctx: Ctx, data: SchoolCreate) -> School:
    db = ctx.db
    if db.scalar(select(School.id).where(School.code == data.code)):
        raise Conflict("School code already in use", code="SCHOOL_CODE_TAKEN")
    school = School(**data.model_dump())
    db.add(school)
    db.flush()
    # Child rows are tenant-scoped: switch the transaction to the new school.
    set_tenant(db, school.id)
    grading.create_default_scale(db, school.id)
    db.add(ConsentText(school_id=school.id, version=1, body=DEFAULT_CONSENT, is_current=True))
    db.flush()
    audit.record(ctx, audit.Action.SCHOOL_CREATE, entity="school", entity_id=school.id, school_id=school.id)
    set_tenant(db, None)
    return school


def get_school_admin(ctx: Ctx, school_id: uuid.UUID) -> School:
    school = ctx.db.get(School, school_id)
    if school is None:
        raise NotFound("School")
    audit.record(ctx, audit.Action.PLATFORM_ADMIN_ACCESS, entity="school", entity_id=school_id, school_id=school_id)
    return school


def set_school_active(ctx: Ctx, school_id: uuid.UUID, active: bool) -> School:
    school = get_school_admin(ctx, school_id)
    school.is_active = active
    return school


def add_staff(ctx: Ctx, school_id: uuid.UUID, data: StaffCreate) -> StaffOut:
    db = ctx.db
    user = get_or_create_user(db, data.phone, data.full_name)
    role = ensure_role(db, user.id, data.role, school_id)
    audit.record(
        ctx,
        audit.Action.STAFF_ROLE_GRANT,
        entity="user_role",
        entity_id=role.id,
        new={"role": data.role.value},
        school_id=school_id,
    )
    return StaffOut(
        role_id=role.id,
        user_id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        role=role.role,
        is_active=role.is_active,
    )


def list_staff(ctx: Ctx, school_id: uuid.UUID) -> list[StaffOut]:
    rows = ctx.db.execute(
        select(UserRole, User)
        .join(User, User.id == UserRole.user_id)
        .where(UserRole.school_id == school_id, UserRole.role.in_([RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL]))
        .order_by(UserRole.role, User.full_name)
    ).all()
    return [
        StaffOut(role_id=r.id, user_id=u.id, full_name=u.full_name, phone=u.phone, role=r.role, is_active=r.is_active)
        for r, u in rows
    ]


def deactivate_staff(ctx: Ctx, school_id: uuid.UUID, role_id: uuid.UUID) -> None:
    role = ctx.db.scalar(
        select(UserRole).where(
            UserRole.id == role_id,
            UserRole.school_id == school_id,
            UserRole.role.in_([RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL]),
        )
    )
    if role is None:
        raise NotFound("Staff role")
    if role.id == ctx.user.user_role_id:
        raise ValidationFailed("You cannot remove your own access")
    role.is_active = False


# ------------------------------------------------------- school profile
def get_own_school(ctx: Ctx) -> School:
    school = ctx.db.get(School, ctx.school_id)
    if school is None:
        raise NotFound("School")
    return school


def update_own_school(ctx: Ctx, data: SchoolUpdate) -> School:
    school = get_own_school(ctx)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(school, k, v)
    ctx.db.flush()
    ctx.db.refresh(school)
    return school


def upload_logo(ctx: Ctx, content: bytes, content_type: str) -> School:
    ext = ALLOWED_LOGO_TYPES.get(content_type)
    if ext is None:
        raise ValidationFailed("Logo must be a PNG or JPEG image")
    if len(content) > 1024 * 1024:
        raise ValidationFailed("Logo must be under 1 MB")
    if not (content.startswith(b"\x89PNG") or content.startswith(b"\xff\xd8")):
        raise ValidationFailed("File is not a valid PNG or JPEG image")
    school = get_own_school(ctx)
    key = f"logos/{school.id}.{ext}"
    get_storage().put(key, content, content_type)
    school.logo_url = key
    return school


def logo_bytes(school: School) -> tuple[bytes, str] | None:
    if not school.logo_url:
        return None
    data = get_storage().get(school.logo_url)
    if data is None:
        return None
    return data, "image/png" if school.logo_url.endswith(".png") else "image/jpeg"


# --------------------------------------------------------------- public
def public_school(db: Session, code: str) -> School:
    school = db.scalar(select(School).where(School.code == code.upper(), School.is_active.is_(True)))
    if school is None:
        raise NotFound("School")
    return school


def to_public(school: School) -> PublicSchool:
    return PublicSchool(
        code=school.code,
        name=school.name,
        board=school.board,
        address=school.address,
        city=school.city,
        state=school.state,
        pincode=school.pincode,
        phone=school.phone,
        email=school.email,
        has_logo=bool(school.logo_url),
    )


def create_demo_request(db: Session, data: DemoRequestIn) -> None:
    # Plain INSERT without RETURNING: the API role may insert leads but never read them.
    db.execute(insert(DemoRequest).values(id=uuid.uuid4(), **data.model_dump()))
