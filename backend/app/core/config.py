"""Application settings, read from environment variables (never from git)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEV_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["local", "test", "staging", "production"] = "local"

    # Database: the API connects as a NON-owner role so Postgres RLS applies.
    database_url: str = "postgresql+psycopg://app_user:app_user_dev@localhost:5433/vidyatrack"
    # Owner role, used only by Alembic migrations and the seed/admin scripts.
    migration_database_url: str = "postgresql+psycopg://vidya_owner:vidya_owner_dev@localhost:5433/vidyatrack"
    app_db_role: str = "app_user"

    redis_url: str | None = None

    # Auth
    jwt_secret: str = _INSECURE_DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    otp_ttl_minutes: int = 5
    otp_max_verify_attempts: int = 5
    otp_requests_per_phone_per_10min: int = 3
    otp_requests_per_ip_per_hour: int = 20
    student_max_failed_logins: int = 5
    student_lockout_minutes: int = 15

    # Dev OTP: logs the OTP and accepts a fixed code. Refused outside local/test.
    dev_otp_enabled: bool = False
    dev_otp_code: str = "123456"

    # SMS provider (DLT-registered template). "console" only allowed in local/test.
    sms_backend: Literal["console", "http"] = "console"
    sms_http_url: str | None = None
    sms_http_api_key: str | None = None

    # Files
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = ".storage"
    s3_bucket: str | None = None
    s3_region: str = "ap-south-1"
    max_upload_mb: int = 5
    max_import_rows: int = 5000

    # Push
    push_backend: Literal["log", "fcm"] = "log"
    fcm_project_id: str | None = None
    fcm_service_account_file: str | None = None

    # Web
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    refresh_cookie_name: str = "vt_refresh"
    cookie_secure: bool = False

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.env in ("staging", "production"):
            if self.dev_otp_enabled:
                raise ValueError("DEV_OTP_ENABLED must be false outside local/test")
            if self.jwt_secret == _INSECURE_DEV_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be set to a strong secret outside local/test")
            if self.sms_backend == "console":
                raise ValueError("SMS_BACKEND=console is not allowed outside local/test")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true outside local/test")
        return self

    @property
    def is_dev(self) -> bool:
        return self.env in ("local", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
