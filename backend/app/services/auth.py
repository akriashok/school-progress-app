"""Authentication: phone OTP, role sessions, rotating refresh tokens, student PIN login."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import set_tenant
from app.core.errors import Forbidden, RateLimited, Unauthorized
from app.core.ratelimit import get_limiter
from app.core.security import (
    create_access_token,
    create_otp_ticket,
    decode_otp_ticket,
    generate_otp,
    hash_otp,
    hash_refresh_token,
    new_refresh_token,
    otp_matches,
)
from app.models import OtpCode, RefreshToken, RoleType, School, Student, User, UserRole
from app.schemas.auth import RoleOption
from app.services import audit, sms
from app.services.phone import InvalidPhone, normalize_phone


def _now() -> datetime:
    return datetime.now(UTC)


def _phone_or_401(raw: str) -> str:
    try:
        return normalize_phone(raw)
    except InvalidPhone as exc:
        raise Unauthorized("Invalid phone or code", code="OTP_INVALID") from exc


# ------------------------------------------------------------------ OTP flow
def request_otp(db: Session, raw_phone: str, ip: str | None) -> None:
    s = get_settings()
    try:
        phone = normalize_phone(raw_phone)
    except InvalidPhone:
        return  # same 200 response; never reveal anything
    limiter = get_limiter()
    if not limiter.hit(f"otp:ip:{ip}", s.otp_requests_per_ip_per_hour, 3600):
        raise RateLimited("Too many OTP requests. Try again later.")
    if not limiter.hit(f"otp:phone:{phone}", s.otp_requests_per_phone_per_10min, 600):
        raise RateLimited("Too many OTP requests for this number. Try again in 10 minutes.")

    user = db.scalar(select(User).where(User.phone == phone, User.is_active.is_(True)))
    if user is None or not _active_roles(db, user.id):
        return
    code = generate_otp()
    db.add(
        OtpCode(phone=phone, code_hash=hash_otp(phone, code), expires_at=_now() + timedelta(minutes=s.otp_ttl_minutes))
    )
    db.flush()
    sms.send_otp(phone, code)


def verify_otp(db: Session, raw_phone: str, code: str) -> tuple[str, list[RoleOption]]:
    s = get_settings()
    phone = _phone_or_401(raw_phone)
    user = db.scalar(select(User).where(User.phone == phone, User.is_active.is_(True)))

    ok = False
    if s.dev_otp_enabled and s.is_dev and code == s.dev_otp_code:
        ok = user is not None
    else:
        otp = db.scalar(
            select(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.consumed_at.is_(None), OtpCode.expires_at > _now())
            .order_by(OtpCode.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        if otp is not None and otp.attempts < s.otp_max_verify_attempts:
            if otp_matches(otp.code_hash, phone, code):
                otp.consumed_at = _now()
                ok = user is not None
            else:
                otp.attempts += 1
                db.commit()  # persist the failed attempt before raising
        elif otp is not None:
            raise Unauthorized("Too many wrong attempts. Request a new OTP.", code="OTP_LOCKED")

    if not ok or user is None:
        raise Unauthorized("Invalid phone or code", code="OTP_INVALID")
    return create_otp_ticket(phone), list_role_options(db, user.id)


def _active_roles(db: Session, user_id: uuid.UUID) -> list[tuple[UserRole, School | None]]:
    rows = db.execute(
        select(UserRole, School)
        .outerjoin(School, School.id == UserRole.school_id)
        .where(UserRole.user_id == user_id, UserRole.is_active.is_(True))
        .order_by(School.name.nulls_first(), UserRole.role)
    ).all()
    return [(r, sc) for r, sc in rows if sc is None or sc.is_active]


def list_role_options(db: Session, user_id: uuid.UUID) -> list[RoleOption]:
    return [
        RoleOption(
            role_id=r.id,
            role=r.role,
            school_id=r.school_id,
            school_name=sc.name if sc else None,
            school_code=sc.code if sc else None,
        )
        for r, sc in _active_roles(db, user_id)
    ]


# ------------------------------------------------------------------ sessions
def _claims(role: UserRole) -> dict[str, str | None]:
    return {
        "sub": str(role.user_id),
        "rid": str(role.id),
        "role": role.role.value,
        "sid": str(role.school_id) if role.school_id else None,
        "tid": str(role.teacher_id) if role.teacher_id else None,
        "gid": str(role.guardian_id) if role.guardian_id else None,
        "stid": str(role.student_id) if role.student_id else None,
    }


def issue_tokens(db: Session, role: UserRole, user_agent: str | None) -> tuple[str, int, str]:
    access, expires_in = create_access_token(_claims(role))
    refresh = new_refresh_token()
    db.add(
        RefreshToken(
            user_role_id=role.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=_now() + timedelta(days=get_settings().refresh_token_days),
            user_agent=(user_agent or "")[:300] or None,
        )
    )
    db.flush()
    return access, expires_in, refresh


def _load_active_role(db: Session, role_id: uuid.UUID, user_id: uuid.UUID) -> UserRole:
    for role, _school in _active_roles(db, user_id):
        if role.id == role_id:
            return role
    raise Forbidden("This role is not available for your account", code="ROLE_NOT_ALLOWED")


def create_session(
    db: Session, ticket: str, role_id: uuid.UUID, user_agent: str | None, ip: str | None
) -> tuple[str, int, str]:
    try:
        phone = decode_otp_ticket(ticket)
    except jwt.PyJWTError as exc:
        raise Unauthorized("Login expired. Please verify OTP again.", code="TICKET_INVALID") from exc
    user = db.scalar(select(User).where(User.phone == phone, User.is_active.is_(True)))
    if user is None:
        raise Unauthorized("Login expired. Please verify OTP again.", code="TICKET_INVALID")
    role = _load_active_role(db, role_id, user.id)
    return _start(db, user, role, user_agent, ip)


def switch_role(
    db: Session, user_id: uuid.UUID, role_id: uuid.UUID, user_agent: str | None, ip: str | None
) -> tuple[str, int, str]:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Account disabled")
    role = _load_active_role(db, role_id, user.id)
    return _start(db, user, role, user_agent, ip)


def _start(db: Session, user: User, role: UserRole, user_agent: str | None, ip: str | None) -> tuple[str, int, str]:
    user.last_login_at = _now()
    tokens = issue_tokens(db, role, user_agent)
    audit.write(
        db,
        audit.Action.LOGIN,
        school_id=role.school_id,
        user_id=user.id,
        role=role.role,
        entity="user_role",
        entity_id=role.id,
        ip=ip,
    )
    return tokens


def refresh(db: Session, token: str, user_agent: str | None) -> tuple[str, int, str]:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token)).with_for_update())
    if row is None:
        raise Unauthorized("Session expired. Please log in again.", code="REFRESH_INVALID")
    if row.revoked_at is not None:
        # Reuse of a rotated token: assume theft and revoke the whole session family.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_role_id == row.user_role_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        db.commit()
        raise Unauthorized("Session expired. Please log in again.", code="REFRESH_REUSED")
    if row.expires_at <= _now():
        raise Unauthorized("Session expired. Please log in again.", code="REFRESH_EXPIRED")
    role = db.get(UserRole, row.user_role_id)
    user = db.get(User, role.user_id) if role else None
    if role is None or user is None or not role.is_active or not user.is_active:
        raise Unauthorized("Account disabled", code="ACCOUNT_DISABLED")
    if role.school_id is not None:
        school = db.get(School, role.school_id)
        if school is None or not school.is_active:
            raise Unauthorized("Account disabled", code="ACCOUNT_DISABLED")
    access, expires_in, new_token = issue_tokens(db, role, user_agent)
    new_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(new_token)))
    row.revoked_at = _now()
    row.replaced_by = new_row.id if new_row else None
    return access, expires_in, new_token


def logout(db: Session, token: str | None) -> None:
    if not token:
        return
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token)))
    if row is not None and row.revoked_at is None:
        row.revoked_at = _now()
        role = db.get(UserRole, row.user_role_id)
        if role is not None:
            audit.write(
                db,
                audit.Action.LOGOUT,
                school_id=role.school_id,
                user_id=role.user_id,
                role=role.role,
                entity="user_role",
                entity_id=role.id,
            )


# ------------------------------------------------------------- student login
def student_login(
    db: Session, school_code: str, admission_no: str, pin: str, user_agent: str | None, ip: str | None
) -> tuple[str, int, str]:
    from app.core.security import verify_pin

    s = get_settings()
    if not get_limiter().hit(f"student:ip:{ip}", 30, 600):
        raise RateLimited("Too many login attempts. Try again later.")
    invalid = Unauthorized("School code, admission number or PIN is wrong", code="STUDENT_LOGIN_INVALID")

    school = db.scalar(select(School).where(School.code == school_code.strip().upper(), School.is_active.is_(True)))
    if school is None:
        raise invalid
    set_tenant(db, school.id)
    student = db.scalar(
        select(Student)
        .where(
            Student.school_id == school.id, Student.admission_no == admission_no.strip(), Student.deleted_at.is_(None)
        )
        .with_for_update()
    )
    if student is None or student.pin_hash is None:
        raise invalid
    if student.locked_until and student.locked_until > _now():
        raise Unauthorized(
            "Too many wrong PINs. Try again in 15 minutes or ask the school office.", code="STUDENT_LOCKED"
        )
    if not verify_pin(student.pin_hash, pin):
        student.failed_logins += 1
        if student.failed_logins >= s.student_max_failed_logins:
            student.locked_until = _now() + timedelta(minutes=s.student_lockout_minutes)
            student.failed_logins = 0
        audit.write(
            db,
            audit.Action.LOGIN_FAILED,
            school_id=school.id,
            user_id=None,
            role=RoleType.STUDENT,
            entity="student",
            entity_id=student.id,
            ip=ip,
        )
        db.commit()
        raise invalid

    student.failed_logins = 0
    student.locked_until = None
    role = db.scalar(
        select(UserRole).where(
            UserRole.student_id == student.id, UserRole.role == RoleType.STUDENT, UserRole.is_active.is_(True)
        )
    )
    user = db.get(User, role.user_id) if role else None
    if role is None or user is None or not user.is_active:
        raise invalid
    return _start(db, user, role, user_agent, ip)
