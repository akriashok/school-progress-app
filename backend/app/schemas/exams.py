import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import MarkStatus, SubmissionStatus
from app.schemas.common import ORM


# ------------------------------------------------------------------ exams
class ExamIn(BaseModel):
    academic_year_id: uuid.UUID
    name: str = Field(min_length=1, max_length=80)
    sequence: int = Field(ge=1, le=50)
    grade_scale_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class ExamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    sequence: int | None = Field(None, ge=1, le=50)
    grade_scale_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class ExamOut(ORM):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    sequence: int
    grade_scale_id: uuid.UUID | None
    start_date: date | None
    end_date: date | None


class ExamSubjectIn(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    max_marks: Decimal = Field(gt=0, le=1000, decimal_places=2)
    pass_marks: Decimal | None = Field(None, ge=0, decimal_places=2)
    exam_date: date | None = None

    @model_validator(mode="after")
    def _pass_le_max(self) -> "ExamSubjectIn":
        if self.pass_marks is not None and self.pass_marks > self.max_marks:
            raise ValueError("pass_marks cannot exceed max_marks")
        return self


class ExamSubjectsIn(BaseModel):
    items: list[ExamSubjectIn] = Field(min_length=1)


class AutoExamSubjectsIn(BaseModel):
    max_marks: Decimal = Field(gt=0, le=1000)
    pass_marks: Decimal | None = Field(None, ge=0)
    class_ids: list[uuid.UUID] | None = Field(None, description="Default: all classes with sections")


class ExamSubjectOut(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    subject_id: uuid.UUID
    subject_name: str
    max_marks: Decimal
    pass_marks: Decimal | None
    effective_pass_marks: Decimal
    exam_date: date | None


# ------------------------------------------------------------------ marks
class MyAssignment(BaseModel):
    section_id: uuid.UUID
    section_name: str
    class_id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: str
    academic_year_id: uuid.UUID
    student_count: int
    is_class_teacher: bool


class MarkRow(BaseModel):
    student_id: uuid.UUID
    admission_no: str
    roll_no: str | None
    full_name: str
    status: MarkStatus | None
    marks: Decimal | None
    version: int | None


class MarksGrid(BaseModel):
    exam_id: uuid.UUID
    exam_name: str
    exam_subject_id: uuid.UUID
    subject_name: str
    section_id: uuid.UUID
    section_name: str
    max_marks: Decimal
    pass_marks: Decimal
    submission_status: SubmissionStatus | None
    submitted_at: datetime | None
    published: bool
    can_edit: bool
    reason_required: bool
    rows: list[MarkRow]


class MarkEntry(BaseModel):
    student_id: uuid.UUID
    marks: Decimal | None = None
    status: MarkStatus = MarkStatus.PRESENT


class BulkMarksIn(BaseModel):
    exam_subject_id: uuid.UUID
    section_id: uuid.UUID
    entries: list[MarkEntry] = Field(max_length=500)
    reason: str | None = Field(None, max_length=500, description="Required when editing published results")


class BulkMarksOut(BaseModel):
    created: int
    updated: int
    unchanged: int


class SubmitMarksIn(BaseModel):
    exam_subject_id: uuid.UUID
    section_id: uuid.UUID


class SubmissionOut(BaseModel):
    exam_subject_id: uuid.UUID
    section_id: uuid.UUID
    status: SubmissionStatus
    submitted_at: datetime | None


class ExamStatusRow(BaseModel):
    section_id: uuid.UUID
    section_name: str
    class_id: uuid.UUID
    exam_subject_id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: str
    teachers: list[str]
    students: int
    entered: int
    status: Literal["NOT_STARTED", "DRAFT", "SUBMITTED"]
    published: bool


class ExamStatus(BaseModel):
    exam_id: uuid.UUID
    total: int
    submitted: int
    pending: int
    rows: list[ExamStatusRow]


class PublicationIn(BaseModel):
    section_ids: list[uuid.UUID] | None = Field(None, description="Omit to (un)publish the whole exam")


class PublicationOut(BaseModel):
    section_id: uuid.UUID
    section_name: str
    published_at: datetime


# ---------------------------------------------------------------- results
class ChildOut(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_no: str
    section_name: str | None
    school_name: str
    relation: str | None


class ExamResultSummary(BaseModel):
    exam_id: uuid.UUID
    exam_name: str
    sequence: int
    academic_year_id: uuid.UUID
    section_id: uuid.UUID
    total_obtained: Decimal
    total_max: Decimal
    percentage: Decimal | None
    grade: str | None
    passed: bool
    subjects_failed: int
    rank: int | None
    section_size: int
    published: bool


class SubjectResult(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    max_marks: Decimal
    pass_marks: Decimal
    status: MarkStatus
    marks: Decimal | None
    percentage: Decimal | None
    grade: str | None
    passed: bool | None


class ExamResultDetail(ExamResultSummary):
    student_id: uuid.UUID
    student_name: str
    subjects: list[SubjectResult]


class ProgressPoint(BaseModel):
    exam_id: uuid.UUID
    exam_name: str
    sequence: int
    percentage: Decimal | None


class SubjectSeries(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    points: list[ProgressPoint]


class Progress(BaseModel):
    student_id: uuid.UUID
    academic_year_id: uuid.UUID | None
    overall: list[ProgressPoint]
    subjects: list[SubjectSeries]


# -------------------------------------------------------------- dashboard
class GradeCount(BaseModel):
    grade: str
    count: int


class DashboardSummary(BaseModel):
    exam_id: uuid.UUID
    exam_name: str
    students: int
    students_with_results: int
    average_percent: Decimal | None
    pass_percent: Decimal | None
    grade_distribution: list[GradeCount]
    sections_published: int
    sections_total: int


class SectionPerformance(BaseModel):
    section_id: uuid.UUID
    section_name: str
    class_id: uuid.UUID
    class_name: str
    students: int
    average_percent: Decimal | None
    pass_percent: Decimal | None
    published: bool


class SubjectPerformance(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    students: int
    average_percent: Decimal | None
    pass_percent: Decimal | None


class AttentionStudent(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_no: str
    section_id: uuid.UUID
    section_name: str
    percentage: Decimal | None
    previous_percentage: Decimal | None
    drop: Decimal | None
    subjects_failed: int
    reasons: list[str]


class Topper(BaseModel):
    section_id: uuid.UUID
    section_name: str
    student_id: uuid.UUID
    full_name: str
    admission_no: str
    percentage: Decimal | None
    grade: str | None
    rank: int


class SectionStudentResult(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_no: str
    roll_no: str | None
    total_obtained: Decimal | None
    total_max: Decimal | None
    percentage: Decimal | None
    grade: str | None
    rank: int | None
    subjects_failed: int | None
    passed: bool | None
