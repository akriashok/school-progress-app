"""Request dependencies: authentication, the tenant guard and role checks.

Every endpoint that touches school-owned data must depend on ``tenant_ctx``
(or ``require_roles(...)``, which builds on it). It is the ONLY place a
``school_id`` is chosen, and it always comes from the verified JWT.
"""

import ipaddress
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, set_tenant
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.models import RoleType

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    user_role_id: uuid.UUID
    role: RoleType
    school_id: uuid.UUID | None
    teacher_id: uuid.UUID | None = None
    guardian_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None

    @property
    def is_staff(self) -> bool:
        return self.role in (RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL, RoleType.TEACHER)

    @property
    def is_school_manager(self) -> bool:
        return self.role in (RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL)


@dataclass
class Ctx:
    """What services receive: a tenant-scoped session plus who is asking."""

    db: Session
    user: CurrentUser
    ip: str | None = None

    @property
    def school_id(self) -> uuid.UUID:
        if self.user.school_id is None:
            raise Forbidden("This action needs a school role")
        return self.user.school_id


def _uuid_or_none(v: object) -> uuid.UUID | None:
    return uuid.UUID(str(v)) if v else None


def client_ip(request: Request) -> str | None:
    """Client IP for audit rows (only if it parses as an IP; inet column)."""
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None


def get_db() -> Iterator[Session]:
    """Session without a tenant (auth flows, platform admin). RLS hides all school rows."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbDep = Annotated[Session, Depends(get_db, scope="function")]


def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise Unauthorized("Missing bearer token")
    try:
        claims = decode_access_token(creds.credentials)
        return CurrentUser(
            user_id=uuid.UUID(claims["sub"]),
            user_role_id=uuid.UUID(claims["rid"]),
            role=RoleType(claims["role"]),
            school_id=_uuid_or_none(claims.get("sid")),
            teacher_id=_uuid_or_none(claims.get("tid")),
            guardian_id=_uuid_or_none(claims.get("gid")),
            student_id=_uuid_or_none(claims.get("stid")),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Unauthorized("Invalid or expired token", code="TOKEN_INVALID") from exc


UserDep = Annotated[CurrentUser, Depends(current_user)]


def tenant_ctx(request: Request, user: UserDep) -> Iterator[Ctx]:
    """The tenant guard: one transaction per request, scoped to the token's school."""
    session = SessionLocal()
    set_tenant(session, user.school_id)
    request.state.user_id = str(user.user_id)
    request.state.school_id = str(user.school_id) if user.school_id else None
    try:
        yield Ctx(db=session, user=user, ip=client_ip(request))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


CtxDep = Annotated[Ctx, Depends(tenant_ctx, scope="function")]


def require_roles(*roles: RoleType) -> Callable[[Ctx], Ctx]:
    allowed = set(roles)

    def _check(ctx: CtxDep) -> Ctx:
        if ctx.user.role not in allowed:
            raise Forbidden()
        return ctx

    return _check


ADMIN = (RoleType.SCHOOL_ADMIN,)
MANAGERS = (RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL)
STAFF = (RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL, RoleType.TEACHER)
FAMILY = (RoleType.PARENT, RoleType.STUDENT)
SCHOOL_ROLES = STAFF + FAMILY

AdminCtx = Annotated[Ctx, Depends(require_roles(*ADMIN))]
ManagerCtx = Annotated[Ctx, Depends(require_roles(*MANAGERS))]
StaffCtx = Annotated[Ctx, Depends(require_roles(*STAFF))]
TeacherCtx = Annotated[Ctx, Depends(require_roles(RoleType.TEACHER))]
ParentCtx = Annotated[Ctx, Depends(require_roles(RoleType.PARENT))]
AnySchoolCtx = Annotated[Ctx, Depends(require_roles(*SCHOOL_ROLES))]
PlatformCtx = Annotated[Ctx, Depends(require_roles(RoleType.PLATFORM_ADMIN))]
