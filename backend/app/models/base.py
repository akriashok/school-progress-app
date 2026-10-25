import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


def pg_enum(py_enum: type[enum.Enum], name: str) -> Any:
    """Map to an existing Postgres enum type (created by the migration)."""
    return Enum(py_enum, name=name, create_type=False, values_callable=lambda e: [m.value for m in e])


class RoleType(enum.StrEnum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    PRINCIPAL = "PRINCIPAL"
    TEACHER = "TEACHER"
    PARENT = "PARENT"
    STUDENT = "STUDENT"


class Gender(enum.StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class GuardianRelation(enum.StrEnum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"


class MarkStatus(enum.StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    EXEMPT = "EXEMPT"


class SubmissionStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


class ImportType(enum.StrEnum):
    STUDENTS = "STUDENTS"
    TEACHERS = "TEACHERS"
    MARKS = "MARKS"


class ImportStatus(enum.StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
