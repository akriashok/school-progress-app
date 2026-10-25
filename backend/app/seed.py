"""Demo data for local development: `python -m app.seed [--reset]`.

1 school (DEMO01), year 2026-27, classes 6-8 x sections A/B, 6 subjects,
10 teachers, 120 students with parents, 2 exams with random marks.
Never run against staging/production.
"""

import argparse
import random
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select, text

from app.core.config import get_settings
from app.core.db import SessionLocal, set_tenant
from app.core.deps import Ctx, CurrentUser
from app.models import (
    ExamSubject,
    Gender,
    GuardianRelation,
    MarkStatus,
    RoleType,
    School,
    SchoolClass,
    Section,
    TeacherAssignment,
    UserRole,
)
from app.schemas.exams import AutoExamSubjectsIn, ExamIn
from app.schemas.setup import (
    AcademicYearIn,
    ClassIn,
    GuardianIn,
    SchoolCreate,
    SectionIn,
    StaffCreate,
    StudentIn,
    SubjectIn,
    TeacherIn,
)
from app.schemas.website import Admissions, GalleryItem, Leader, StatItem
from app.services import academics, exams, marks, people, schools, website
from app.services.users import ensure_role, get_or_create_user

PLATFORM_ADMIN_PHONE = "+919000000000"
SCHOOL_ADMIN_PHONE = "+919000000001"
PRINCIPAL_PHONE = "+919000000002"
STUDENT_PIN = "1234"

FIRST_BOYS = [
    "Aarav",
    "Vihaan",
    "Arjun",
    "Sai",
    "Reyansh",
    "Krishna",
    "Ishaan",
    "Rohan",
    "Karthik",
    "Aditya",
    "Rahul",
    "Nikhil",
    "Varun",
    "Harsha",
    "Teja",
    "Pranav",
    "Akhil",
    "Charan",
    "Manoj",
    "Siddharth",
]
FIRST_GIRLS = [
    "Ananya",
    "Diya",
    "Saanvi",
    "Aadhya",
    "Lakshmi",
    "Sneha",
    "Keerthi",
    "Divya",
    "Harika",
    "Pooja",
    "Meghana",
    "Sravani",
    "Nithya",
    "Bhavya",
    "Tejaswini",
    "Swathi",
    "Kavya",
    "Ishita",
    "Riya",
    "Navya",
]
SURNAMES = [
    "Reddy",
    "Rao",
    "Sharma",
    "Naidu",
    "Kumar",
    "Varma",
    "Chowdary",
    "Goud",
    "Yadav",
    "Patel",
    "Iyer",
    "Gupta",
    "Srinivas",
    "Prasad",
    "Murthy",
]
SUBJECTS = [
    ("English", "ENG"),
    ("Hindi", "HIN"),
    ("Telugu", "TEL"),
    ("Mathematics", "MATH"),
    ("Science", "SCI"),
    ("Social Studies", "SOC"),
]
TEACHERS = [
    "Lakshmi Devi",
    "Ravi Kumar",
    "Sunita Sharma",
    "Venkat Rao",
    "Padma Reddy",
    "Suresh Naidu",
    "Anitha Varma",
    "Mohan Prasad",
    "Kalyani Iyer",
    "Srinivas Goud",
]


def reset_database() -> None:
    s = get_settings()
    if not s.is_dev:
        sys.exit("Refusing to reset a non-dev database")
    engine = create_engine(s.migration_database_url)
    with engine.begin() as conn:
        tables = (
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
            )
            .scalars()
            .all()
        )
        conn.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"))
    engine.dispose()
    print("Database reset.")


def seed() -> None:
    rnd = random.Random(42)
    db = SessionLocal()
    try:
        if db.scalar(select(School.id).where(School.code == "DEMO01")):
            print("Demo school already exists. Use --reset to recreate it.")
            return

        # Platform admin
        pa_user = get_or_create_user(db, PLATFORM_ADMIN_PHONE, "Platform Admin")
        pa_role = ensure_role(db, pa_user.id, RoleType.PLATFORM_ADMIN, None)
        pa_ctx = Ctx(
            db=db,
            user=CurrentUser(user_id=pa_user.id, user_role_id=pa_role.id, role=RoleType.PLATFORM_ADMIN, school_id=None),
        )
        school = schools.create_school(
            pa_ctx,
            SchoolCreate(
                code="DEMO01",
                name="Sri Vidya High School",
                board="CBSE",
                address="Plot 12, MG Road",
                city="Hyderabad",
                state="Telangana",
                pincode="500001",
                phone="+914012345678",
                email="office@srividya.example",
            ),
        )
        admin = schools.add_staff(
            pa_ctx,
            school.id,
            StaffCreate(full_name="Office Admin", phone=SCHOOL_ADMIN_PHONE, role=RoleType.SCHOOL_ADMIN),
        )
        schools.add_staff(
            pa_ctx,
            school.id,
            StaffCreate(full_name="Dr. Meera Krishnan", phone=PRINCIPAL_PHONE, role=RoleType.PRINCIPAL),
        )

        set_tenant(db, school.id)
        ctx = Ctx(
            db=db,
            user=CurrentUser(
                user_id=admin.user_id, user_role_id=admin.role_id, role=RoleType.SCHOOL_ADMIN, school_id=school.id
            ),
        )

        year = academics.create_year(
            ctx,
            AcademicYearIn(name="2026-27", start_date=date(2026, 6, 1), end_date=date(2027, 3, 31), is_current=True),
        )
        classes = [academics.create_class(ctx, ClassIn(name=str(n), sort_order=n)) for n in (6, 7, 8)]
        subjects = [academics.create_subject(ctx, SubjectIn(name=n, code=c)) for n, c in SUBJECTS]
        sections: list[Section] = []
        for c in classes:
            for name in ("A", "B"):
                out = academics.create_section(ctx, SectionIn(academic_year_id=year.id, class_id=c.id, name=name))
                sec = db.get(Section, out.id)
                assert sec is not None
                sections.append(sec)
                academics.set_section_subjects(ctx, sec.id, [s.id for s in subjects])

        teachers = []
        for i, name in enumerate(TEACHERS, start=1):
            t = people.create_teacher(
                ctx,
                TeacherIn(
                    full_name=name, phone=f"+9191000000{i:02d}", employee_code=f"T{i:03d}", designation="Teacher"
                ),
            )
            teachers.append(t)
        # Each subject has a main teacher; sections share teachers across classes.
        for si, sec in enumerate(sections):
            sec.class_teacher_id = teachers[si % len(teachers)].id
            for j, subj in enumerate(subjects):
                teacher = teachers[(j + (si % 2) * 6) % len(teachers)]
                db.add(
                    TeacherAssignment(school_id=school.id, teacher_id=teacher.id, section_id=sec.id, subject_id=subj.id)
                )
        db.flush()

        n_student = 0
        shared_parent_phones: list[tuple[str, str]] = []
        for sec in sections:
            cls = db.get(SchoolClass, sec.class_id)
            assert cls is not None
            for roll in range(1, 21):
                n_student += 1
                girl = rnd.random() < 0.5
                first = rnd.choice(FIRST_GIRLS if girl else FIRST_BOYS)
                surname = rnd.choice(SURNAMES)
                birth_year = 2026 - int(cls.name) - 6
                st, _ = people.upsert_student(
                    ctx,
                    StudentIn(
                        admission_no=f"A{1000 + n_student}",
                        full_name=f"{first} {surname}",
                        date_of_birth=date(birth_year, rnd.randint(1, 12), rnd.randint(1, 28)),
                        gender=Gender.FEMALE if girl else Gender.MALE,
                        section_id=sec.id,
                        roll_no=str(roll),
                    ),
                )
                people.set_student_pin(ctx, st.id, STUDENT_PIN)
                # Every 10th student is a sibling of an earlier one (same father).
                if n_student % 10 == 0 and shared_parent_phones:
                    f_phone, f_name = rnd.choice(shared_parent_phones)
                else:
                    f_phone, f_name = f"+9192{n_student:08d}", f"{rnd.choice(FIRST_BOYS)} {surname}"
                    shared_parent_phones.append((f_phone, f_name))
                father, _ = people.upsert_guardian(ctx, GuardianIn(full_name=f_name, phone=f_phone))
                people.link_guardian_ids(ctx, st.id, father.id, GuardianRelation.FATHER, True)
                if n_student % 3 == 0:
                    mother, _ = people.upsert_guardian(
                        ctx, GuardianIn(full_name=f"{rnd.choice(FIRST_GIRLS)} {surname}", phone=f"+9193{n_student:08d}")
                    )
                    people.link_guardian_ids(ctx, st.id, mother.id, GuardianRelation.MOTHER, False)

        # Exams
        ut1 = exams.create_exam(
            ctx,
            ExamIn(
                academic_year_id=year.id,
                name="Unit Test 1",
                sequence=1,
                start_date=date(2026, 7, 20),
                end_date=date(2026, 7, 25),
            ),
        )
        hy = exams.create_exam(
            ctx,
            ExamIn(
                academic_year_id=year.id,
                name="Half-Yearly",
                sequence=2,
                start_date=date(2026, 9, 21),
                end_date=date(2026, 9, 30),
            ),
        )
        exams.auto_exam_subjects(ctx, ut1.id, AutoExamSubjectsIn(max_marks=Decimal(25)))
        exams.auto_exam_subjects(ctx, hy.id, AutoExamSubjectsIn(max_marks=Decimal(100)))
        exams.create_exam(
            ctx,
            ExamIn(
                academic_year_id=year.id,
                name="Annual",
                sequence=3,
                start_date=date(2027, 3, 1),
                end_date=date(2027, 3, 15),
            ),
        )

        ability: dict[uuid.UUID, float] = {}
        for exam in (ut1, hy):
            for es in db.scalars(select(ExamSubject).where(ExamSubject.exam_id == exam.id)):
                for sec in [s for s in sections if s.class_id == es.class_id]:
                    scope = marks.load_scope(ctx, es.id, sec.id)
                    entries: list[tuple[uuid.UUID, MarkStatus, Decimal | None]] = []
                    for st, _e in marks.enrolled_students(ctx, sec):
                        base = ability.setdefault(st.id, rnd.uniform(0.35, 0.95))
                        if rnd.random() < 0.02:
                            entries.append((st.id, MarkStatus.ABSENT, None))
                            continue
                        drift = rnd.uniform(-0.15, 0.12) if exam is hy else rnd.uniform(-0.08, 0.08)
                        frac = min(max(base + drift, 0.05), 1.0)
                        value = (es.max_marks * Decimal(str(round(frac, 3)))).quantize(Decimal("1"))
                        entries.append((st.id, MarkStatus.PRESENT, value))
                    marks.apply_entries(ctx, scope, entries, None, source="seed")
                    if exam is ut1 or sec.name == "A":
                        sub_ctx = Ctx(
                            db=db,
                            user=CurrentUser(
                                user_id=admin.user_id,
                                user_role_id=admin.role_id,
                                role=RoleType.SCHOOL_ADMIN,
                                school_id=school.id,
                            ),
                        )
                        marks.submit(sub_ctx, es.id, sec.id)
        marks.publish(ctx, ut1.id, None)
        marks.publish(ctx, hy.id, [s.id for s in sections if s.name == "A"])
        seed_website(ctx)
        db.commit()

        # Print demo logins
        first_parent = shared_parent_phones[0][0]
        print("Seeded demo school DEMO01 (Sri Vidya High School).")
        print("Dev OTP (DEV_OTP_ENABLED=true): 123456")
        print(f"  Platform admin : {PLATFORM_ADMIN_PHONE}")
        print(f"  School admin   : {SCHOOL_ADMIN_PHONE}")
        print(f"  Principal      : {PRINCIPAL_PHONE}")
        print("  Teacher        : +919100000001")
        print(f"  Parent         : {first_parent}")
        print(f"  Student        : school DEMO01, admission A1001, PIN {STUDENT_PIN}")
    finally:
        db.close()


ASSETS = Path(__file__).parent / "demo_assets"


def _img(ctx: Ctx, name: str) -> str:
    return website.upload_image(ctx, (ASSETS / f"{name}.jpg").read_bytes(), "image/jpeg")


def seed_website(ctx: Ctx) -> None:
    """Demo content + illustrations for the public school website (fictional school)."""
    content = website.default_content(schools.get_own_school(ctx))
    content.tagline = "CBSE · Nursery to Class 10 · Hyderabad"
    content.hero_title = "Where every child learns, plays and shines"
    content.hero_image = _img(ctx, "hero")
    content.about_image = _img(ctx, "about")
    for card, name in zip(content.highlights, ("academics", "activities", "values"), strict=False):
        card.image = _img(ctx, name)
    for fac, name in zip(content.facilities, ("classroom", "library", "playground", "bus"), strict=False):
        fac.image = _img(ctx, name)
    content.stats = [
        StatItem(value="120+", label="Students"),
        StatItem(value="6", label="Sections"),
        StatItem(value="10", label="Teachers"),
        StatItem(value="15", label="Years of trust"),
    ]
    content.excellence = [
        "Experienced, caring teachers",
        "Spoken English and public speaking",
        "Safe campus with CCTV",
        "Regular parent updates on the VidyaTrack app",
    ]
    content.gallery = [
        GalleryItem(image=_img(ctx, name), caption=caption)
        for name, caption in (
            ("sports", "Sports day"),
            ("art", "Art class"),
            ("science", "Science lab"),
            ("music", "Music room"),
            ("annual", "Annual day"),
            ("garden", "School garden"),
        )
    ]
    content.leaders = [
        Leader(
            name="Dr. Meera Krishnan",
            role="Principal",
            bio="25 years in school education; believes every child can excel.",
            photo=_img(ctx, "principal"),
        )
    ]
    content.admissions = Admissions(
        open=True,
        title="Admissions open for 2027-28",
        body="Visit the school office or message us on WhatsApp to book a campus tour.",
    )
    content.contact.whatsapp = "+919000000001"
    content.contact.timings = "Mon-Sat, 8:30 am - 4:00 pm"
    website.save_content(ctx, content)


def refresh_demo_website() -> None:
    """Re-apply the demo website (texts + illustrations) to an existing DEMO01 school."""
    db = SessionLocal()
    try:
        school = db.scalar(select(School).where(School.code == "DEMO01"))
        if school is None:
            sys.exit("Demo school not found; run `python -m app.seed` first")
        set_tenant(db, school.id)
        role = db.scalar(
            select(UserRole).where(UserRole.school_id == school.id, UserRole.role == RoleType.SCHOOL_ADMIN)
        )
        assert role is not None
        ctx = Ctx(
            db=db,
            user=CurrentUser(
                user_id=role.user_id, user_role_id=role.id, role=RoleType.SCHOOL_ADMIN, school_id=school.id
            ),
        )
        seed_website(ctx)
        db.commit()
        print("Demo school website refreshed.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="truncate all tables first (dev only)")
    parser.add_argument("--website", action="store_true", help="only refresh the demo school website")
    args = parser.parse_args()
    if not get_settings().is_dev:
        sys.exit("Seeding is only allowed in local/test environments")
    if args.website:
        refresh_demo_website()
        return
    if args.reset:
        reset_database()
    seed()


if __name__ == "__main__":
    main()
