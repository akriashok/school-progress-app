"""Tenant isolation: school B can never read or write school A's data.

Two layers are tested separately: Postgres RLS on its own (raw SQL as the API
role), and the API, where every read endpoint must 404 for another school's ids.
"""

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal, set_tenant
from tests.factories import put_marks

SCHOOL_TABLES = [
    "academic_years",
    "classes",
    "subjects",
    "teachers",
    "sections",
    "section_subjects",
    "teacher_assignments",
    "students",
    "student_enrolments",
    "guardians",
    "student_guardians",
    "grade_scales",
    "exams",
    "exam_subjects",
    "marks",
    "marks_submissions",
    "result_publications",
    "consent_texts",
    "consents",
    "imports",
]


# ---------------------------------------------------------------- RLS layer
def test_rls_scopes_raw_sql_to_the_session_school(world) -> None:  # type: ignore[no-untyped-def]
    with SessionLocal() as db:
        set_tenant(db, world.a.school_id)
        schools_seen = db.execute(text("SELECT DISTINCT school_id FROM students")).scalars().all()
        assert schools_seen == [world.a.school_id]
        # Even an explicit filter for school B returns nothing.
        n = db.execute(text("SELECT count(*) FROM students WHERE school_id = :b"), {"b": world.b.school_id}).scalar()
        assert n == 0


@pytest.mark.parametrize("table", SCHOOL_TABLES)
def test_rls_without_tenant_sees_nothing(world, table: str) -> None:  # type: ignore[no-untyped-def]
    with SessionLocal() as db:
        set_tenant(db, None)
        assert db.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0  # noqa: S608


def test_rls_blocks_cross_school_insert(world) -> None:  # type: ignore[no-untyped-def]
    with SessionLocal() as db:
        set_tenant(db, world.a.school_id)
        with pytest.raises(Exception, match="row-level security"):
            db.execute(
                text("INSERT INTO classes (id, school_id, name, sort_order) VALUES (gen_random_uuid(), :b, 'X', 1)"),
                {"b": world.b.school_id},
            )


def test_results_view_respects_rls(client, world) -> None:  # type: ignore[no-untyped-def]
    put_marks(client, world.a.h("admin"), world.a.e1_math, world.a.sec_a, [{"student_id": world.a.s1, "marks": 50}])
    with SessionLocal() as db:
        set_tenant(db, world.b.school_id)
        assert db.execute(text("SELECT count(*) FROM v_student_exam_results")).scalar() == 0
        set_tenant(db, world.a.school_id)
        assert db.execute(text("SELECT count(*) FROM v_student_exam_results")).scalar() == 1


def test_api_role_cannot_bypass_rls(world) -> None:  # type: ignore[no-untyped-def]
    with SessionLocal() as db:
        row = db.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")).one()
        assert row == (False, False)
        owner = db.execute(text("SELECT tableowner FROM pg_tables WHERE tablename = 'marks'")).scalar()
        assert owner != db.execute(text("SELECT current_user")).scalar()


# ----------------------------------------------------------------- API layer
def _a_urls(w):  # type: ignore[no-untyped-def]
    a = w.a
    return [
        f"/api/v1/students/{a.s1}",
        f"/api/v1/students/{a.s1}/guardians",
        f"/api/v1/students/{a.s1}/results",
        f"/api/v1/students/{a.s1}/results/{a.e1}",
        f"/api/v1/students/{a.s1}/progress",
        f"/api/v1/students/{a.s1}/report-cards/{a.e1}.pdf",
        f"/api/v1/teachers/{a.t1}",
        f"/api/v1/guardians/{a.p1}",
        f"/api/v1/sections/{a.sec_a}",
        f"/api/v1/sections/{a.sec_a}/subjects",
        f"/api/v1/exams/{a.e1}",
        f"/api/v1/exams/{a.e1}/subjects",
        f"/api/v1/exams/{a.e1}/status",
        f"/api/v1/exams/{a.e1}/publications",
        f"/api/v1/marks?exam_subject_id={a.e1_math}&section_id={a.sec_a}",
        f"/api/v1/dashboard/summary?exam_id={a.e1}",
        f"/api/v1/dashboard/sections?exam_id={a.e1}",
        f"/api/v1/dashboard/subjects?exam_id={a.e1}",
        f"/api/v1/dashboard/attention?exam_id={a.e1}",
        f"/api/v1/dashboard/toppers?exam_id={a.e1}",
        f"/api/v1/dashboard/students?exam_id={a.e1}&section_id={a.sec_a}",
        f"/api/v1/dashboard/export?report=sections&exam_id={a.e1}",
        f"/api/v1/imports/templates/marks?exam_subject_id={a.e1_math}&section_id={a.sec_a}",
    ]


@pytest.mark.parametrize("who", ["admin", "principal"])
def test_other_school_gets_404_on_every_read(client, world, who: str) -> None:  # type: ignore[no-untyped-def]
    for url in _a_urls(world):
        r = client.get(url, headers=world.b.h(who))
        assert r.status_code == 404, (url, r.status_code, r.text)


def test_other_school_lists_never_include_school_a(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.b.h("admin")
    a_ids = {str(world.a.s1), str(world.a.s2), str(world.a.s3), str(world.a.s4)}
    students = client.get("/api/v1/students", headers=h).json()["items"]
    assert students and not a_ids & {s["id"] for s in students}
    for url in ("/api/v1/teachers", "/api/v1/guardians"):
        items = client.get(url, headers=h).json()["items"]
        assert all("SCHA" not in i["full_name"] for i in items)
    for url in (
        "/api/v1/sections",
        "/api/v1/exams",
        "/api/v1/subjects",
        "/api/v1/classes",
        "/api/v1/academic-years",
        "/api/v1/teacher-assignments",
        "/api/v1/grade-scales",
    ):
        r = client.get(url, headers=h)
        assert r.status_code == 200
        ids = {x["id"] for x in r.json()}
        assert str(world.a.sec_a) not in ids and str(world.a.e1) not in ids


def test_other_school_cannot_write(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.b.h("admin")
    a = world.a
    assert client.patch(f"/api/v1/students/{a.s1}", headers=h, json={"full_name": "X"}).status_code == 404
    assert client.delete(f"/api/v1/students/{a.s1}", headers=h).status_code == 404
    assert client.post(f"/api/v1/students/{a.s1}/pin", headers=h, json={"pin": "1111"}).status_code == 404
    assert client.patch(f"/api/v1/sections/{a.sec_a}", headers=h, json={"name": "Z"}).status_code == 404
    assert client.delete(f"/api/v1/exams/{a.e1}", headers=h).status_code == 404
    r = put_marks(client, h, a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 99}])
    assert r.status_code == 404
    r = client.post(f"/api/v1/exams/{a.e1}/publications", headers=world.b.h("principal"), json={})
    assert r.status_code == 404
    # Mixing ids: school B's own section with school A's student
    r = client.post(
        "/api/v1/students", headers=h, json={"admission_no": "X1", "full_name": "X", "section_id": str(a.sec_a)}
    )
    assert r.status_code == 404


def test_school_id_in_body_is_ignored(client, world) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/subjects", headers=world.b.h("admin"), json={"name": "Art", "school_id": str(world.a.school_id)}
    )
    assert r.status_code == 201
    names_a = [s["name"] for s in client.get("/api/v1/subjects", headers=world.a.h("admin")).json()]
    assert "Art" not in names_a


def test_other_school_teacher_and_family(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    r = client.get(f"/api/v1/marks?exam_subject_id={a.e1_math}&section_id={a.sec_a}", headers=world.b.h("teacher1"))
    assert r.status_code == 404
    for who in ("parent1", "student_s1"):
        assert client.get(f"/api/v1/students/{a.s1}/results", headers=world.b.h(who)).status_code == 404
