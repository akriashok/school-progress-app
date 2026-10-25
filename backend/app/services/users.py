"""Linking people (teachers, guardians, staff, students) to global users and per-school roles."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RoleType, User, UserRole


def get_or_create_user(db: Session, phone: str | None, full_name: str) -> User:
    if phone:
        user = db.scalar(select(User).where(User.phone == phone))
        if user is not None:
            return user
    user = User(phone=phone, full_name=full_name)
    db.add(user)
    db.flush()
    return user


def ensure_role(
    db: Session,
    user_id: uuid.UUID,
    role: RoleType,
    school_id: uuid.UUID | None,
    *,
    teacher_id: uuid.UUID | None = None,
    guardian_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
) -> UserRole:
    stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role == role)
    stmt = stmt.where(UserRole.school_id.is_(None) if school_id is None else UserRole.school_id == school_id)
    ur = db.scalar(stmt)
    if ur is None:
        ur = UserRole(
            user_id=user_id,
            role=role,
            school_id=school_id,
            teacher_id=teacher_id,
            guardian_id=guardian_id,
            student_id=student_id,
        )
        db.add(ur)
    else:
        ur.is_active = True
        ur.teacher_id = teacher_id or ur.teacher_id
        ur.guardian_id = guardian_id or ur.guardian_id
        ur.student_id = student_id or ur.student_id
    db.flush()
    return ur


def deactivate_roles(
    db: Session,
    school_id: uuid.UUID,
    *,
    teacher_id: uuid.UUID | None = None,
    guardian_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
) -> None:
    stmt = select(UserRole).where(UserRole.school_id == school_id)
    if teacher_id:
        stmt = stmt.where(UserRole.teacher_id == teacher_id, UserRole.role == RoleType.TEACHER)
    elif guardian_id:
        stmt = stmt.where(UserRole.guardian_id == guardian_id, UserRole.role == RoleType.PARENT)
    elif student_id:
        stmt = stmt.where(UserRole.student_id == student_id, UserRole.role == RoleType.STUDENT)
    else:
        return
    for ur in db.scalars(stmt):
        ur.is_active = False
    db.flush()
