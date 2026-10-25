import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models import RoleType

ClientType = Literal["app", "web"]


class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=16)


class OtpVerify(BaseModel):
    phone: str = Field(min_length=10, max_length=16)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class RoleOption(BaseModel):
    role_id: uuid.UUID
    role: RoleType
    school_id: uuid.UUID | None
    school_name: str | None
    school_code: str | None


class OtpVerified(BaseModel):
    ticket: str = Field(description="Short-lived proof of OTP; exchange it at /auth/session")
    roles: list[RoleOption]


class SessionRequest(BaseModel):
    ticket: str
    role_id: uuid.UUID
    client: ClientType = "app"


class StudentLogin(BaseModel):
    school_code: str = Field(min_length=2, max_length=12)
    admission_no: str = Field(min_length=1, max_length=30)
    pin: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")
    client: ClientType = "app"


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(None, description="App clients; web uses the httpOnly cookie")


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret
    expires_in: int
    refresh_token: str | None = Field(None, description="Omitted for web clients (sent as cookie)")


class Me(BaseModel):
    user_id: uuid.UUID
    full_name: str
    role: RoleType
    role_id: uuid.UUID
    school_id: uuid.UUID | None
    school_name: str | None
    school_code: str | None
    teacher_id: uuid.UUID | None
    guardian_id: uuid.UUID | None
    student_id: uuid.UUID | None
    consent_required: bool
    other_roles: list[RoleOption]
