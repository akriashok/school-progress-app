"""Builds two small schools (A and B) through the real services, plus role tokens."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.core.db import SessionLocal, set_tenant
from app.core.deps import Ctx, CurrentUser
from app.core.security import create_access_token
from app.models import GuardianRelation, RoleType, UserRole
from app.schemas.exams import ExamIn, ExamSubjectIn
from app.schemas.setup import (
    AcademicYearIn,
    AssignmentIn,
    ClassIn,
    GuardianIn,
    SchoolCreate,
    SectionIn,
    StaffCreate,
    StudentIn,
    SubjectIn,
    TeacherIn,
)
from app.services import academics, exams, people, schools
from app.services.auth import _claims
from app.services.users import ensure_role, get_or_create_user


def bearer(role: UserRole) -> dict[str, str]:
    token, _ = create_access_token(_claims(role))
    return {"Authorization": f"Bearer {token}"}


@dataclass
class SchoolWorld:
    code: str
    ids: dict[str, Any] = field(default_factory=dict)
    roles: dict[str, UserRole] = field(default_factory=dict)

    def h(self, who: str) -> dict[str, str]:
        return bearer(self.roles[who])

    def __getattr__(self, name: str) -> Any:
        try:
            return self.__dict__["ids"][name]
        except KeyError as exc:
            raise AttributeError(name) from exc


@dataclass
class World:
    a: SchoolWorld
    b: SchoolWorld
    platform_admin: UserRole

    def platform(self) -> dict[str, str]:
        return bearer(self.platform_admin)


def _ctx_for(db: Any, role: UserRole) -> Ctx:
    return Ctx(
        db=db,
        user=CurrentUser(
            user_id=role.user_id,
            user_role_id=role.id,
            role=role.role,
            school_id=role.school_id,
            teacher_id=role.teacher_id,
            guardian_id=role.guardian_id,
            student_id=role.student_id,
        ),
    )


def _find_role(db: Any, **kw: Any) -> UserRole:
    from sqlalchemy import select

    stmt = select(UserRole)
    for k, v in kw.items():
        stmt = stmt.where(getattr(UserRole, k) == v)
    role = db.scalar(stmt)
    assert role is not None, kw
    return role


def make_school(db: Any, pa_ctx: Ctx, code: str, phone_prefix: str) -> SchoolWorld:
    w = SchoolWorld(code=code)
    school = schools.create_school(pa_ctx, SchoolCreate(code=code, name=f"School {code}", city="Hyderabad"))
    w.ids["school_id"] = school.id
    admin = schools.add_staff(
        pa_ctx,
        school.id,
        StaffCreate(full_name=f"Admin {code}", phone=f"{phone_prefix}00001", role=RoleType.SCHOOL_ADMIN),
    )
    principal = schools.add_staff(
        pa_ctx,
        school.id,
        StaffCreate(full_name=f"Principal {code}", phone=f"{phone_prefix}00002", role=RoleType.PRINCIPAL),
    )
    set_tenant(db, school.id)
    w.roles["admin"] = _find_role(db, id=admin.role_id)
    w.roles["principal"] = _find_role(db, id=principal.role_id)
    ctx = _ctx_for(db, w.roles["admin"])

    year = academics.create_year(
        ctx, AcademicYearIn(name="2026-27", start_date=date(2026, 6, 1), end_date=date(2027, 3, 31), is_current=True)
    )
    cls = academics.create_class(ctx, ClassIn(name="7", sort_order=7))
    sec_a = academics.create_section(ctx, SectionIn(academic_year_id=year.id, class_id=cls.id, name="A"))
    sec_b = academics.create_section(ctx, SectionIn(academic_year_id=year.id, class_id=cls.id, name="B"))
    math = academics.create_subject(ctx, SubjectIn(name="Mathematics", code="MATH"))
    sci = academics.create_subject(ctx, SubjectIn(name="Science", code="SCI"))
    eng = academics.create_subject(ctx, SubjectIn(name="English", code="ENG"))
    w.ids.update(year_id=year.id, class_id=cls.id, sec_a=sec_a.id, sec_b=sec_b.id, math=math.id, sci=sci.id, eng=eng.id)

    t1 = people.create_teacher(ctx, TeacherIn(full_name=f"Teacher One {code}", phone=f"{phone_prefix}00011"))
    t2 = people.create_teacher(ctx, TeacherIn(full_name=f"Teacher Two {code}", phone=f"{phone_prefix}00012"))
    for sec, subj, t in (
        (sec_a.id, math.id, t1),
        (sec_a.id, sci.id, t1),
        (sec_a.id, eng.id, t2),
        (sec_b.id, math.id, t2),
    ):
        people.create_assignment(ctx, AssignmentIn(teacher_id=t.id, section_id=sec, subject_id=subj))
    w.ids.update(t1=t1.id, t2=t2.id)
    w.roles["teacher1"] = _find_role(db, teacher_id=t1.id)
    w.roles["teacher2"] = _find_role(db, teacher_id=t2.id)

    for key, adm, name, sec, roll in (
        ("s1", "S1", "Asha", sec_a.id, "1"),
        ("s2", "S2", "Bala", sec_a.id, "2"),
        ("s3", "S3", "Chitra", sec_a.id, "3"),
        ("s4", "S4", "Deepak", sec_b.id, "1"),
    ):
        st = people.create_student(
            ctx, StudentIn(admission_no=f"{code}-{adm}", full_name=f"{name} {code}", section_id=sec, roll_no=roll)
        )
        people.set_student_pin(ctx, st.id, "4321")
        w.ids[key] = st.id
        w.roles[f"student_{key}"] = _find_role(db, student_id=st.id)

    p1, _ = people.upsert_guardian(ctx, GuardianIn(full_name=f"Parent One {code}", phone=f"{phone_prefix}00021"))
    p2, _ = people.upsert_guardian(ctx, GuardianIn(full_name=f"Parent Two {code}", phone=f"{phone_prefix}00022"))
    people.link_guardian_ids(ctx, w.s1, p1.id, GuardianRelation.FATHER, True)
    people.link_guardian_ids(ctx, w.s2, p2.id, GuardianRelation.MOTHER, True)
    w.ids.update(p1=p1.id, p2=p2.id)
    w.roles["parent1"] = _find_role(db, guardian_id=p1.id)
    w.roles["parent2"] = _find_role(db, guardian_id=p2.id)

    e1 = exams.create_exam(ctx, ExamIn(academic_year_id=year.id, name="Unit Test 1", sequence=1))
    e2 = exams.create_exam(ctx, ExamIn(academic_year_id=year.id, name="Half-Yearly", sequence=2))
    for e in (e1, e2):
        rows = exams.upsert_exam_subjects(
            ctx,
            e.id,
            [ExamSubjectIn(class_id=cls.id, subject_id=s, max_marks=Decimal(100)) for s in (math.id, sci.id, eng.id)],
        )
        for r in rows:
            key = {math.id: "math", sci.id: "sci", eng.id: "eng"}[r.subject_id]
            w.ids[f"{'e1' if e is e1 else 'e2'}_{key}"] = r.id
    w.ids.update(e1=e1.id, e2=e2.id)
    set_tenant(db, None)
    return w


def build_world() -> World:
    db = SessionLocal()
    try:
        pa_user = get_or_create_user(db, "+919999999999", "Platform Admin")
        pa_role = ensure_role(db, pa_user.id, RoleType.PLATFORM_ADMIN, None)
        pa_ctx = _ctx_for(db, pa_role)
        a = make_school(db, pa_ctx, "SCHA", "+9198000")
        b = make_school(db, pa_ctx, "SCHB", "+9197000")
        db.commit()
        # Accept consent for parents by default so most tests focus on their subject.
        for w in (a, b):
            set_tenant(db, w.school_id)
            from app.services import consent

            for p in ("parent1", "parent2"):
                consent.accept(_ctx_for(db, w.roles[p]), 1, "pytest")
            db.commit()
        return World(a=a, b=b, platform_admin=pa_role)
    finally:
        db.close()


def put_marks(
    client: Any,
    headers: dict[str, str],
    es_id: Any,
    section_id: Any,
    entries: list[dict[str, Any]],
    reason: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "exam_subject_id": str(es_id),
        "section_id": str(section_id),
        "entries": [{**e, "student_id": str(e["student_id"])} for e in entries],
    }
    if reason:
        body["reason"] = reason
    return client.put("/api/v1/marks/bulk", headers=headers, json=body)
