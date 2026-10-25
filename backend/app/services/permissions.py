"""Row-level permission helpers (DESIGN.md §5).

Convention: when a caller is not allowed to see a specific record (another
school, another child), raise NotFound so ids can't be probed. When the role
can never do an action, raise Forbidden.
"""

import uuid

from sqlalchemy import exists, select

from app.core.deps import Ctx
from app.core.errors import Forbidden, NotFound
from app.models import (
    RoleType,
    Section,
    Student,
    StudentEnrolment,
    StudentGuardian,
    TeacherAssignment,
)


def teacher_can_access(ctx: Ctx, section_id: uuid.UUID, subject_id: uuid.UUID) -> bool:
    if ctx.user.role != RoleType.TEACHER or ctx.user.teacher_id is None:
        return False
    stmt = select(
        exists().where(
            TeacherAssignment.school_id == ctx.school_id,
            TeacherAssignment.teacher_id == ctx.user.teacher_id,
            TeacherAssignment.section_id == section_id,
            TeacherAssignment.subject_id == subject_id,
        )
    )
    return bool(ctx.db.scalar(stmt))


def teacher_teaches_section(ctx: Ctx, section_id: uuid.UUID) -> bool:
    if ctx.user.teacher_id is None:
        return False
    assigned = exists().where(
        TeacherAssignment.school_id == ctx.school_id,
        TeacherAssignment.teacher_id == ctx.user.teacher_id,
        TeacherAssignment.section_id == section_id,
    )
    class_teacher = exists().where(
        Section.school_id == ctx.school_id,
        Section.id == section_id,
        Section.class_teacher_id == ctx.user.teacher_id,
    )
    return bool(ctx.db.scalar(select(assigned | class_teacher)))


def guardian_can_access(ctx: Ctx, student_id: uuid.UUID) -> bool:
    if ctx.user.role != RoleType.PARENT or ctx.user.guardian_id is None:
        return False
    stmt = select(
        exists().where(
            StudentGuardian.school_id == ctx.school_id,
            StudentGuardian.guardian_id == ctx.user.guardian_id,
            StudentGuardian.student_id == student_id,
        )
    )
    return bool(ctx.db.scalar(stmt))


def _teacher_can_see_student(ctx: Ctx, student_id: uuid.UUID) -> bool:
    if ctx.user.teacher_id is None:
        return False
    taught_sections = (
        select(TeacherAssignment.section_id)
        .where(
            TeacherAssignment.school_id == ctx.school_id,
            TeacherAssignment.teacher_id == ctx.user.teacher_id,
        )
        .union(
            select(Section.id).where(
                Section.school_id == ctx.school_id, Section.class_teacher_id == ctx.user.teacher_id
            )
        )
    )
    stmt = select(
        exists().where(
            StudentEnrolment.school_id == ctx.school_id,
            StudentEnrolment.student_id == student_id,
            StudentEnrolment.section_id.in_(taught_sections),
        )
    )
    return bool(ctx.db.scalar(stmt))


def ensure_student_visible(ctx: Ctx, student_id: uuid.UUID) -> Student:
    """Return the student if the caller may see them; otherwise 404."""
    student = ctx.db.scalar(
        select(Student).where(
            Student.id == student_id, Student.school_id == ctx.school_id, Student.deleted_at.is_(None)
        )
    )
    if student is None:
        raise NotFound("Student")
    role = ctx.user.role
    allowed = (
        role in (RoleType.SCHOOL_ADMIN, RoleType.PRINCIPAL)
        or (role == RoleType.TEACHER and _teacher_can_see_student(ctx, student_id))
        or (role == RoleType.PARENT and guardian_can_access(ctx, student_id))
        or (role == RoleType.STUDENT and ctx.user.student_id == student_id)
    )
    if not allowed:
        raise NotFound("Student")
    return student


def only_published(ctx: Ctx) -> bool:
    """Parents and students only ever see published results."""
    return ctx.user.role in (RoleType.PARENT, RoleType.STUDENT)


def ensure_section_in_school(ctx: Ctx, section_id: uuid.UUID) -> Section:
    section = ctx.db.scalar(select(Section).where(Section.id == section_id, Section.school_id == ctx.school_id))
    if section is None:
        raise NotFound("Section")
    return section


def ensure_can_view_section(ctx: Ctx, section_id: uuid.UUID) -> Section:
    section = ensure_section_in_school(ctx, section_id)
    if ctx.user.is_school_manager:
        return section
    if ctx.user.role == RoleType.TEACHER and teacher_teaches_section(ctx, section_id):
        return section
    raise Forbidden()
