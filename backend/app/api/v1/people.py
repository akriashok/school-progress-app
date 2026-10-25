import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import AdminCtx, ManagerCtx
from app.schemas.common import Ok, Page, PageParams
from app.schemas.setup import (
    AssignmentIn,
    AssignmentOut,
    GuardianIn,
    GuardianLinkIn,
    GuardianOut,
    GuardianUpdate,
    PinIn,
    StudentDetail,
    StudentGuardianOut,
    StudentIn,
    StudentOut,
    StudentUpdate,
    TeacherIn,
    TeacherOut,
    TeacherUpdate,
)
from app.services import people as svc

router = APIRouter(tags=["people"])
PageQ = Annotated[PageParams, Query()]


# ---------------------------------------------------------------- teachers
@router.get("/teachers", response_model=Page[TeacherOut])
def list_teachers(ctx: ManagerCtx, params: PageQ, q: str | None = None) -> Page[TeacherOut]:
    return svc.list_teachers(ctx, params, q)


@router.post("/teachers", response_model=TeacherOut, status_code=201)
def create_teacher(body: TeacherIn, ctx: AdminCtx) -> TeacherOut:
    return TeacherOut.model_validate(svc.create_teacher(ctx, body))


@router.get("/teachers/{teacher_id}", response_model=TeacherOut)
def get_teacher(teacher_id: uuid.UUID, ctx: ManagerCtx) -> TeacherOut:
    return TeacherOut.model_validate(svc.get_teacher(ctx, teacher_id))


@router.patch("/teachers/{teacher_id}", response_model=TeacherOut)
def update_teacher(teacher_id: uuid.UUID, body: TeacherUpdate, ctx: AdminCtx) -> TeacherOut:
    return TeacherOut.model_validate(svc.update_teacher(ctx, teacher_id, body))


@router.delete("/teachers/{teacher_id}", response_model=Ok, summary="Soft delete; removes assignments")
def delete_teacher(teacher_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_teacher(ctx, teacher_id)
    return Ok()


# ------------------------------------------------------------- assignments
@router.get("/teacher-assignments", response_model=list[AssignmentOut])
def list_assignments(
    ctx: ManagerCtx,
    teacher_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    academic_year_id: uuid.UUID | None = None,
) -> list[AssignmentOut]:
    return svc.list_assignments(ctx, teacher_id=teacher_id, section_id=section_id, academic_year_id=academic_year_id)


@router.post("/teacher-assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(body: AssignmentIn, ctx: AdminCtx) -> AssignmentOut:
    return svc.create_assignment(ctx, body)


@router.delete("/teacher-assignments/{assignment_id}", response_model=Ok)
def delete_assignment(assignment_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_assignment(ctx, assignment_id)
    return Ok()


# ---------------------------------------------------------------- students
@router.get("/students", response_model=Page[StudentOut])
def list_students(
    ctx: ManagerCtx,
    params: PageQ,
    section_id: uuid.UUID | None = None,
    academic_year_id: uuid.UUID | None = None,
    q: str | None = None,
) -> Page[StudentOut]:
    return svc.list_students(ctx, params, section_id=section_id, academic_year_id=academic_year_id, q=q)


@router.post("/students", response_model=StudentOut, status_code=201)
def create_student(body: StudentIn, ctx: AdminCtx) -> StudentOut:
    return svc.create_student(ctx, body)


@router.get("/students/{student_id}", response_model=StudentDetail)
def get_student(student_id: uuid.UUID, ctx: ManagerCtx) -> StudentDetail:
    return svc.student_detail(ctx, student_id)


@router.patch("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: uuid.UUID, body: StudentUpdate, ctx: AdminCtx) -> StudentOut:
    return svc.update_student(ctx, student_id, body)


@router.delete("/students/{student_id}", response_model=Ok, summary="Soft delete")
def delete_student(student_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_student(ctx, student_id)
    return Ok()


@router.post("/students/{student_id}/pin", response_model=Ok, summary="Set or reset the student's login PIN")
def set_pin(student_id: uuid.UUID, body: PinIn, ctx: AdminCtx) -> Ok:
    svc.set_student_pin(ctx, student_id, body.pin)
    return Ok()


@router.get("/students/{student_id}/guardians", response_model=list[StudentGuardianOut])
def student_guardians(student_id: uuid.UUID, ctx: ManagerCtx) -> list[StudentGuardianOut]:
    svc.get_student_row(ctx, student_id)
    return svc.list_student_guardians(ctx, student_id)


@router.post("/students/{student_id}/guardians", response_model=list[StudentGuardianOut], status_code=201)
def link_guardian(student_id: uuid.UUID, body: GuardianLinkIn, ctx: AdminCtx) -> list[StudentGuardianOut]:
    return svc.link_guardian(ctx, student_id, body)


@router.delete("/students/{student_id}/guardians/{guardian_id}", response_model=Ok)
def unlink_guardian(student_id: uuid.UUID, guardian_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.unlink_guardian(ctx, student_id, guardian_id)
    return Ok()


# --------------------------------------------------------------- guardians
@router.get("/guardians", response_model=Page[GuardianOut])
def list_guardians(ctx: ManagerCtx, params: PageQ, q: str | None = None) -> Page[GuardianOut]:
    return svc.list_guardians(ctx, params, q)


@router.post("/guardians", response_model=GuardianOut, status_code=201)
def create_guardian(body: GuardianIn, ctx: AdminCtx) -> GuardianOut:
    return GuardianOut.model_validate(svc.create_guardian(ctx, body))


@router.get("/guardians/{guardian_id}", response_model=GuardianOut)
def get_guardian(guardian_id: uuid.UUID, ctx: ManagerCtx) -> GuardianOut:
    return GuardianOut.model_validate(svc.get_guardian(ctx, guardian_id))


@router.patch("/guardians/{guardian_id}", response_model=GuardianOut)
def update_guardian(guardian_id: uuid.UUID, body: GuardianUpdate, ctx: AdminCtx) -> GuardianOut:
    return GuardianOut.model_validate(svc.update_guardian(ctx, guardian_id, body))


@router.delete("/guardians/{guardian_id}", response_model=Ok, summary="Soft delete; unlinks children")
def delete_guardian(guardian_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_guardian(ctx, guardian_id)
    return Ok()
