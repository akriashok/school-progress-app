"""Audit log helper. Writes in the caller's transaction so the log and the change
commit (or roll back) together."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Ctx
from app.models import AuditLog, RoleType


class Action:
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    MARK_CREATE = "MARK_CREATE"
    MARK_UPDATE = "MARK_UPDATE"
    MARKS_SUBMIT = "MARKS_SUBMIT"
    RESULT_PUBLISH = "RESULT_PUBLISH"
    RESULT_UNPUBLISH = "RESULT_UNPUBLISH"
    IMPORT_COMMIT = "IMPORT_COMMIT"
    EXPORT = "EXPORT"
    REPORT_CARD_DOWNLOAD = "REPORT_CARD_DOWNLOAD"
    PIN_RESET = "PIN_RESET"
    CONSENT_ACCEPT = "CONSENT_ACCEPT"
    PLATFORM_ADMIN_ACCESS = "PLATFORM_ADMIN_ACCESS"
    SCHOOL_CREATE = "SCHOOL_CREATE"
    STAFF_ROLE_GRANT = "STAFF_ROLE_GRANT"


def _jsonable(v: dict[str, Any] | None) -> dict[str, Any] | None:
    if v is None:
        return None
    return {k: (str(x) if isinstance(x, uuid.UUID) else x) for k, x in v.items()}


def write(
    db: Session,
    action: str,
    *,
    school_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    role: RoleType | None,
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    old: dict[str, Any] | None = None,
    new: dict[str, Any] | None = None,
    reason: str | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            school_id=school_id,
            user_id=user_id,
            role=role,
            action=action,
            entity=entity,
            entity_id=entity_id,
            old_value=_jsonable(old),
            new_value=_jsonable(new),
            reason=reason,
            ip_address=ip,
        )
    )


def record(
    ctx: Ctx,
    action: str,
    *,
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    old: dict[str, Any] | None = None,
    new: dict[str, Any] | None = None,
    reason: str | None = None,
    school_id: uuid.UUID | None = None,
) -> None:
    write(
        ctx.db,
        action,
        school_id=school_id or ctx.user.school_id,
        user_id=ctx.user.user_id,
        role=ctx.user.role,
        entity=entity,
        entity_id=entity_id,
        old=old,
        new=new,
        reason=reason,
        ip=ctx.ip,
    )


def list_logs(ctx: Ctx, entity_id: uuid.UUID | None, limit: int) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.school_id == ctx.school_id)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    return list(ctx.db.scalars(stmt.order_by(AuditLog.created_at.desc()).limit(limit)))
