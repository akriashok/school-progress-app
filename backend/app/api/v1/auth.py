import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Cookie, Request, Response

from app.core.config import get_settings
from app.core.deps import CtxDep, DbDep, UserDep, client_ip
from app.core.errors import Unauthorized
from app.models import School, User
from app.schemas.auth import (
    ClientType,
    LogoutRequest,
    Me,
    OtpRequest,
    OtpVerified,
    OtpVerify,
    RefreshRequest,
    SessionRequest,
    StudentLogin,
    TokenPair,
)
from app.schemas.common import Ok
from app.services import auth, consent

router = APIRouter(tags=["auth"])


def _ip(request: Request) -> str | None:
    return client_ip(request)


def _tokens(response: Response, tokens: tuple[str, int, str], client: ClientType) -> TokenPair:
    access, expires_in, refresh = tokens
    if client == "web":
        s = get_settings()
        response.set_cookie(
            s.refresh_cookie_name,
            refresh,
            max_age=s.refresh_token_days * 86400,
            httponly=True,
            secure=s.cookie_secure,
            samesite="lax",
            path="/api/v1/auth",
        )
        return TokenPair(access_token=access, expires_in=expires_in)
    return TokenPair(access_token=access, expires_in=expires_in, refresh_token=refresh)


@router.post(
    "/auth/otp/request",
    response_model=Ok,
    summary="Send an OTP. Always 200 (does not reveal whether the number is registered).",
)
def otp_request(body: OtpRequest, request: Request, db: DbDep) -> Ok:
    auth.request_otp(db, body.phone, _ip(request))
    return Ok()


@router.post("/auth/otp/verify", response_model=OtpVerified)
def otp_verify(body: OtpVerify, db: DbDep) -> OtpVerified:
    ticket, roles = auth.verify_otp(db, body.phone, body.otp)
    return OtpVerified(ticket=ticket, roles=roles)


@router.post("/auth/session", response_model=TokenPair, summary="Pick a role/school after OTP; get tokens")
def session(body: SessionRequest, request: Request, response: Response, db: DbDep) -> TokenPair:
    tokens = auth.create_session(db, body.ticket, body.role_id, request.headers.get("user-agent"), _ip(request))
    return _tokens(response, tokens, body.client)


@router.post("/auth/switch", response_model=TokenPair, summary="Switch to another of your roles")
def switch(
    user: UserDep,
    request: Request,
    response: Response,
    db: DbDep,
    role_id: Annotated[uuid.UUID, Body(embed=True)],
    client: Annotated[ClientType, Body(embed=True)] = "app",
) -> TokenPair:
    tokens = auth.switch_role(db, user.user_id, role_id, request.headers.get("user-agent"), _ip(request))
    return _tokens(response, tokens, client)


@router.post("/auth/student/login", response_model=TokenPair)
def student_login(body: StudentLogin, request: Request, response: Response, db: DbDep) -> TokenPair:
    tokens = auth.student_login(
        db, body.school_code, body.admission_no, body.pin, request.headers.get("user-agent"), _ip(request)
    )
    return _tokens(response, tokens, body.client)


@router.post("/auth/refresh", response_model=TokenPair, summary="Rotate the refresh token")
def refresh(
    request: Request,
    response: Response,
    db: DbDep,
    body: RefreshRequest | None = None,
    vt_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenPair:
    token = (body.refresh_token if body else None) or vt_refresh
    if not token:
        raise Unauthorized("Session expired. Please log in again.", code="REFRESH_INVALID")
    tokens = auth.refresh(db, token, request.headers.get("user-agent"))
    return _tokens(response, tokens, "app" if body and body.refresh_token else "web")


@router.post("/auth/logout", response_model=Ok)
def logout(
    response: Response, db: DbDep, body: LogoutRequest | None = None, vt_refresh: Annotated[str | None, Cookie()] = None
) -> Ok:
    auth.logout(db, (body.refresh_token if body else None) or vt_refresh)
    response.delete_cookie(get_settings().refresh_cookie_name, path="/api/v1/auth")
    return Ok()


@router.get("/me", response_model=Me)
def me(ctx: CtxDep) -> Me:
    user = ctx.db.get(User, ctx.user.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Account disabled", code="ACCOUNT_DISABLED")
    school = ctx.db.get(School, ctx.user.school_id) if ctx.user.school_id else None
    others = [r for r in auth.list_role_options(ctx.db, user.id) if r.role_id != ctx.user.user_role_id]
    return Me(
        user_id=user.id,
        full_name=user.full_name,
        role=ctx.user.role,
        role_id=ctx.user.user_role_id,
        school_id=ctx.user.school_id,
        school_name=school.name if school else None,
        school_code=school.code if school else None,
        teacher_id=ctx.user.teacher_id,
        guardian_id=ctx.user.guardian_id,
        student_id=ctx.user.student_id,
        consent_required=consent.is_required(ctx),
        other_roles=others,
    )
