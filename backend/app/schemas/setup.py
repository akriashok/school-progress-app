import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator, model_validator

from app.models import Gender, GuardianRelation, RoleType
from app.schemas.common import ORM
from app.services.phone import normalize_phone

Phone = Annotated[str, BeforeValidator(normalize_phone)]
Name = Annotated[str, Field(min_length=1, max_length=150)]


# ------------------------------------------------------------------ school
class SchoolOut(ORM):
    id: uuid.UUID
    code: str
    name: str
    board: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    phone: str | None
    email: str | None
    logo_url: str | None
    show_rank: bool
    pass_percent: Decimal
    is_active: bool


class SchoolUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    board: str | None = Field(None, max_length=30)
    address: str | None = None
    city: str | None = Field(None, max_length=80)
    state: str | None = Field(None, max_length=80)
    pincode: str | None = Field(None, max_length=10)
    phone: str | None = Field(None, max_length=15)
    email: EmailStr | None = None
    show_rank: bool | None = None
    pass_percent: Decimal | None = Field(None, ge=0, le=100)


class PublicSchool(BaseModel):
    code: str
    name: str
    board: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    phone: str | None
    email: str | None
    has_logo: bool


class SchoolCreate(BaseModel):
    code: str = Field(min_length=3, max_length=12, pattern=r"^[A-Za-z0-9]+$")
    name: str = Field(min_length=2, max_length=200)
    board: str | None = Field(None, max_length=30)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    phone: str | None = None
    email: EmailStr | None = None

    @field_validator("code")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class StaffCreate(BaseModel):
    full_name: Name
    phone: Phone
    role: RoleType = RoleType.SCHOOL_ADMIN

    @field_validator("role")
    @classmethod
    def _staff_role(cls, v: RoleType) -> RoleType:
        if v not in (RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL):
            raise ValueError("role must be SCHOOL_ADMIN or PRINCIPAL")
        return v


class StaffOut(BaseModel):
    role_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    phone: str | None
    role: RoleType
    is_active: bool


class DemoRequestIn(BaseModel):
    name: Name
    school_name: str = Field(min_length=2, max_length=200)
    phone: Phone
    city: str | None = Field(None, max_length=80)
    students: int | None = Field(None, ge=0, le=100000)
    message: str | None = Field(None, max_length=2000)


# ------------------------------------------------------------- academics
class AcademicYearIn(BaseModel):
    name: str = Field(min_length=4, max_length=20)
    start_date: date
    end_date: date
    is_current: bool = False

    @model_validator(mode="after")
    def _dates(self) -> "AcademicYearIn":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class AcademicYearOut(ORM):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    sort_order: int = Field(ge=-10, le=100)


class ClassOut(ORM):
    id: uuid.UUID
    name: str
    sort_order: int


class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str | None = Field(None, max_length=20)


class SubjectOut(ORM):
    id: uuid.UUID
    name: str
    code: str | None


class SectionIn(BaseModel):
    academic_year_id: uuid.UUID
    class_id: uuid.UUID
    name: str = Field(min_length=1, max_length=10)
    class_teacher_id: uuid.UUID | None = None


class SectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=10)
    class_teacher_id: uuid.UUID | None = None


class SectionOut(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    class_sort_order: int
    name: str
    display_name: str
    class_teacher_id: uuid.UUID | None
    class_teacher_name: str | None
    student_count: int


class SectionSubjectsIn(BaseModel):
    subject_ids: list[uuid.UUID]


# ---------------------------------------------------------------- people
class TeacherIn(BaseModel):
    full_name: Name
    phone: Phone
    employee_code: str | None = Field(None, max_length=30)
    email: EmailStr | None = None
    designation: str | None = Field(None, max_length=80)


class TeacherUpdate(BaseModel):
    full_name: Name | None = None
    employee_code: str | None = Field(None, max_length=30)
    email: EmailStr | None = None
    designation: str | None = Field(None, max_length=80)


class TeacherOut(ORM):
    id: uuid.UUID
    full_name: str
    phone: str
    employee_code: str | None
    email: str | None
    designation: str | None


class AssignmentIn(BaseModel):
    teacher_id: uuid.UUID
    section_id: uuid.UUID
    subject_id: uuid.UUID


class AssignmentOut(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: str
    section_id: uuid.UUID
    section_name: str
    subject_id: uuid.UUID
    subject_name: str


class StudentIn(BaseModel):
    admission_no: str = Field(min_length=1, max_length=30)
    full_name: Name
    date_of_birth: date | None = None
    gender: Gender | None = None
    section_id: uuid.UUID
    roll_no: str | None = Field(None, max_length=10)


class StudentUpdate(BaseModel):
    full_name: Name | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    section_id: uuid.UUID | None = None
    roll_no: str | None = Field(None, max_length=10)


class StudentOut(BaseModel):
    id: uuid.UUID
    admission_no: str
    full_name: str
    date_of_birth: date | None
    gender: Gender | None
    section_id: uuid.UUID | None
    section_name: str | None
    class_id: uuid.UUID | None
    roll_no: str | None
    has_pin: bool


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")


class GuardianIn(BaseModel):
    full_name: Name
    phone: Phone
    email: EmailStr | None = None


class GuardianUpdate(BaseModel):
    full_name: Name | None = None
    email: EmailStr | None = None


class GuardianOut(ORM):
    id: uuid.UUID
    full_name: str
    phone: str
    email: str | None


class GuardianLinkIn(BaseModel):
    guardian_id: uuid.UUID | None = None
    guardian: GuardianIn | None = None
    relation: GuardianRelation
    is_primary: bool = False

    @model_validator(mode="after")
    def _one(self) -> "GuardianLinkIn":
        if (self.guardian_id is None) == (self.guardian is None):
            raise ValueError("give exactly one of guardian_id or guardian")
        return self


class StudentGuardianOut(BaseModel):
    guardian_id: uuid.UUID
    full_name: str
    phone: str
    relation: GuardianRelation
    is_primary: bool


class StudentDetail(StudentOut):
    guardians: list[StudentGuardianOut]


# ---------------------------------------------------------- grade scales
class GradeBandIn(BaseModel):
    grade: str = Field(min_length=1, max_length=5)
    min_percent: Decimal = Field(ge=0, le=100)
    max_percent: Decimal = Field(ge=0, le=100)
    grade_point: Decimal | None = Field(None, ge=0, le=10)


class GradeScaleIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    is_default: bool = False
    bands: list[GradeBandIn] = Field(min_length=1)


class GradeBandOut(ORM):
    grade: str
    min_percent: Decimal
    max_percent: Decimal
    grade_point: Decimal | None


class GradeScaleOut(BaseModel):
    id: uuid.UUID
    name: str
    is_default: bool
    bands: list[GradeBandOut]


class AuditOut(ORM):
    id: int
    action: str
    entity: str | None
    entity_id: uuid.UUID | None
    user_id: uuid.UUID | None
    role: RoleType | None
    old_value: dict[str, object] | None
    new_value: dict[str, object] | None
    reason: str | None
    created_at: datetime
