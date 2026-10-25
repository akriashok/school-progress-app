"""ORM models mirroring db/schema.sql (Alembic migrations are the source of truth)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    Gender,
    GuardianRelation,
    ImportStatus,
    ImportType,
    MarkStatus,
    RoleType,
    SubmissionStatus,
    created_at_col,
    pg_enum,
    updated_at_col,
    uuid_pk,
)

UUIDT = UUID(as_uuid=True)


def school_fk() -> Mapped[uuid.UUID]:
    return mapped_column(UUIDT, ForeignKey("schools.id"), nullable=False, index=True)


# --------------------------------------------------------------------- tenancy
class School(Base):
    __tablename__ = "schools"
    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    board: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(80))
    pincode: Mapped[str | None] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(15))
    email: Mapped[str | None] = mapped_column(CITEXT)
    logo_url: Mapped[str | None] = mapped_column(Text)
    show_rank: Mapped[bool] = mapped_column(Boolean, default=True)
    pass_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("33.00"))
    modules: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    branding: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    website: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


# -------------------------------------------------------------------- identity
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str | None] = mapped_column(String(15), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(CITEXT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str] = mapped_column(String(15))
    code_hash: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_role_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("user_roles.id"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(UUIDT)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()


class UserRole(Base):
    __tablename__ = "user_roles"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("users.id"))
    role: Mapped[RoleType] = mapped_column(pg_enum(RoleType, "role_type"))
    school_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("schools.id"))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("teachers.id"))
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("guardians.id"))
    student_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("students.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at_col()


# ------------------------------------------------------- academic structure
class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    name: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class SchoolClass(Base):
    __tablename__ = "classes"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    name: Mapped[str] = mapped_column(String(30))
    sort_order: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    name: Mapped[str] = mapped_column(String(80))
    code: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class Section(Base):
    __tablename__ = "sections"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    academic_year_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("academic_years.id"))
    class_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("classes.id"))
    name: Mapped[str] = mapped_column(String(10))
    class_teacher_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("teachers.id"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class SectionSubject(Base):
    __tablename__ = "section_subjects"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    section_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("sections.id", ondelete="CASCADE"))
    subject_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("subjects.id"))


# ---------------------------------------------------------------------- people
class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("users.id"))
    employee_code: Mapped[str | None] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(15))
    email: Mapped[str | None] = mapped_column(CITEXT)
    designation: Mapped[str | None] = mapped_column(String(80))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("teachers.id"))
    section_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("sections.id", ondelete="CASCADE"))
    subject_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("subjects.id"))
    created_at: Mapped[datetime] = created_at_col()


class Student(Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("users.id"))
    admission_no: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(150))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[Gender | None] = mapped_column(pg_enum(Gender, "gender_type"))
    pin_hash: Mapped[str | None] = mapped_column(Text)
    failed_logins: Mapped[int] = mapped_column(SmallInteger, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class StudentEnrolment(Base):
    __tablename__ = "student_enrolments"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    student_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("students.id"))
    academic_year_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("academic_years.id"))
    section_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("sections.id"))
    roll_no: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = created_at_col()


class Guardian(Base):
    __tablename__ = "guardians"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("users.id"))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(15))
    email: Mapped[str | None] = mapped_column(CITEXT)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class StudentGuardian(Base):
    __tablename__ = "student_guardians"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    student_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("students.id"))
    guardian_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("guardians.id"))
    relation: Mapped[GuardianRelation] = mapped_column(pg_enum(GuardianRelation, "guardian_relation"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


# --------------------------------------------------------------------- grading
class GradeScale(Base):
    __tablename__ = "grade_scales"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    name: Mapped[str] = mapped_column(String(60))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class GradeBand(Base):
    __tablename__ = "grade_bands"
    id: Mapped[uuid.UUID] = uuid_pk()
    grade_scale_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("grade_scales.id", ondelete="CASCADE"))
    grade: Mapped[str] = mapped_column(String(5))
    min_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    max_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    grade_point: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))


# ----------------------------------------------------------------------- exams
class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    academic_year_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("academic_years.id"))
    name: Mapped[str] = mapped_column(String(80))
    sequence: Mapped[int] = mapped_column(SmallInteger)
    grade_scale_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("grade_scales.id"))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class ExamSubject(Base):
    __tablename__ = "exam_subjects"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    exam_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("exams.id", ondelete="CASCADE"))
    class_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("classes.id"))
    subject_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("subjects.id"))
    max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    pass_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    exam_date: Mapped[date | None] = mapped_column(Date)


class Mark(Base):
    __tablename__ = "marks"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    exam_subject_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("exam_subjects.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("students.id"))
    section_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("sections.id"))
    status: Mapped[MarkStatus] = mapped_column(pg_enum(MarkStatus, "mark_status"), default=MarkStatus.PRESENT)
    marks_obtained: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    entered_by: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class MarksSubmission(Base):
    __tablename__ = "marks_submissions"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    exam_subject_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("exam_subjects.id"))
    section_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("sections.id"))
    status: Mapped[SubmissionStatus] = mapped_column(
        pg_enum(SubmissionStatus, "submission_status"), default=SubmissionStatus.DRAFT
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResultPublication(Base):
    __tablename__ = "result_publications"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    exam_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("exams.id"))
    section_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("sections.id"))
    published_by: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("users.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------- consent, devices, imports
class ConsentText(Base):
    __tablename__ = "consent_texts"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_col()


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    guardian_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("guardians.id"))
    consent_text_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("consent_texts.id"))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("users.id"))
    fcm_token: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str] = mapped_column(String(10), default="android")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = created_at_col()


class Import(Base):
    __tablename__ = "imports"
    id: Mapped[uuid.UUID] = uuid_pk()
    school_id: Mapped[uuid.UUID] = school_fk()
    type: Mapped[ImportType] = mapped_column(pg_enum(ImportType, "import_type"))
    status: Mapped[ImportStatus] = mapped_column(pg_enum(ImportStatus, "import_status"), default=ImportStatus.UPLOADED)
    file_key: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    total_rows: Mapped[int | None] = mapped_column(Integer)
    valid_rows: Mapped[int | None] = mapped_column(Integer)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDT, ForeignKey("users.id"))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("schools.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT, ForeignKey("users.id"))
    role: Mapped[RoleType | None] = mapped_column(pg_enum(RoleType, "role_type"))
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUIDT)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = created_at_col()


class DemoRequest(Base):
    """'Book a demo' leads from the public landing page (not school-owned)."""

    __tablename__ = "demo_requests"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(150))
    school_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(15))
    city: Mapped[str | None] = mapped_column(String(80))
    students: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()
