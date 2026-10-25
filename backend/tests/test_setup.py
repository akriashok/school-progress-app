"""School setup CRUD, soft deletes, role checks and platform admin."""

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import AuditLog, GradeScale


def test_academic_year_current_is_unique(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.a.h("admin")
    r = client.post(
        "/api/v1/academic-years",
        headers=h,
        json={"name": "2027-28", "start_date": "2027-06-01", "end_date": "2028-03-31", "is_current": True},
    )
    assert r.status_code == 201
    years = client.get("/api/v1/academic-years", headers=h).json()
    assert [y["name"] for y in years if y["is_current"]] == ["2027-28"]
    bad = client.post(
        "/api/v1/academic-years", headers=h, json={"name": "X", "start_date": "2027-06-01", "end_date": "2027-01-01"}
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "VALIDATION_ERROR"
    dup = client.post(
        "/api/v1/academic-years",
        headers=h,
        json={"name": "2027-28", "start_date": "2027-06-01", "end_date": "2028-03-31"},
    )
    assert dup.status_code == 409


def test_classes_sections_subjects_crud(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    h = a.h("admin")
    c = client.post("/api/v1/classes", headers=h, json={"name": "8", "sort_order": 8}).json()
    s = client.post(
        "/api/v1/sections",
        headers=h,
        json={"academic_year_id": str(a.year_id), "class_id": c["id"], "name": "A", "class_teacher_id": str(a.t1)},
    )
    assert s.status_code == 201 and s.json()["display_name"] == "Class 8-A"
    assert s.json()["class_teacher_name"] == "Teacher One SCHA"
    sid = s.json()["id"]
    r = client.put(f"/api/v1/sections/{sid}/subjects", headers=h, json={"subject_ids": [str(a.math), str(a.sci)]})
    assert sorted(x["name"] for x in r.json()) == ["Mathematics", "Science"]
    r = client.put(f"/api/v1/sections/{sid}/subjects", headers=h, json={"subject_ids": [str(a.math)]})
    assert [x["name"] for x in r.json()] == ["Mathematics"]
    assert client.patch(f"/api/v1/sections/{sid}", headers=h, json={"name": "C"}).json()["name"] == "C"
    # A class in use can't be deleted; an empty one can.
    assert client.delete(f"/api/v1/classes/{c['id']}", headers=h).status_code == 409
    assert client.delete(f"/api/v1/sections/{sid}", headers=h).status_code == 200
    assert client.delete(f"/api/v1/classes/{c['id']}", headers=h).status_code == 200
    subj = client.post("/api/v1/subjects", headers=h, json={"name": "Art"}).json()
    assert (
        client.put(f"/api/v1/subjects/{subj['id']}", headers=h, json={"name": "Fine Art"}).json()["name"] == "Fine Art"
    )
    assert client.post("/api/v1/subjects", headers=h, json={"name": "Fine Art"}).status_code == 409


def test_non_admins_cannot_change_setup(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    for who in ("principal", "teacher1", "parent1", "student_s1"):
        r = client.post("/api/v1/subjects", headers=a.h(who), json={"name": "Art"})
        assert r.status_code == 403, who
    # Principal can read setup; family roles cannot.
    assert client.get("/api/v1/sections", headers=a.h("principal")).status_code == 200
    assert client.get("/api/v1/sections", headers=a.h("parent1")).status_code == 403


def test_teacher_crud_soft_delete(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    h = a.h("admin")
    t = client.post("/api/v1/teachers", headers=h, json={"full_name": "New T", "phone": "98000 55555"})
    assert t.status_code == 201 and t.json()["phone"] == "+919800055555"
    assert (
        client.post("/api/v1/teachers", headers=h, json={"full_name": "Dup", "phone": "9800055555"}).status_code == 409
    )
    bad = client.post("/api/v1/teachers", headers=h, json={"full_name": "Bad", "phone": "12345"})
    assert bad.status_code == 422
    tid = t.json()["id"]
    assert client.delete(f"/api/v1/teachers/{tid}", headers=h).status_code == 200
    assert client.get(f"/api/v1/teachers/{tid}", headers=h).status_code == 404
    names = [x["full_name"] for x in client.get("/api/v1/teachers", headers=h).json()["items"]]
    assert "New T" not in names
    # The deleted teacher's login role is deactivated.
    r = client.post("/api/v1/auth/otp/verify", json={"phone": "9800055555", "otp": "123456"})
    assert r.status_code == 200 and r.json()["roles"] == []


def test_teacher_assignments(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    h = a.h("admin")
    r = client.post(
        "/api/v1/teacher-assignments",
        headers=h,
        json={"teacher_id": str(a.t2), "section_id": str(a.sec_b), "subject_id": str(a.sci)},
    )
    assert r.status_code == 201 and r.json()["section_name"] == "Class 7-B"
    dup = client.post(
        "/api/v1/teacher-assignments",
        headers=h,
        json={"teacher_id": str(a.t2), "section_id": str(a.sec_b), "subject_id": str(a.sci)},
    )
    assert dup.status_code == 409
    listed = client.get(f"/api/v1/teacher-assignments?teacher_id={a.t2}", headers=h).json()
    assert len(listed) == 3
    assert client.delete(f"/api/v1/teacher-assignments/{r.json()['id']}", headers=h).status_code == 200


def test_students_and_guardians(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    h = a.h("admin")
    st = client.post(
        "/api/v1/students",
        headers=h,
        json={
            "admission_no": "N1",
            "full_name": "New Kid",
            "section_id": str(a.sec_b),
            "roll_no": "9",
            "gender": "FEMALE",
            "date_of_birth": "2014-02-03",
        },
    )
    assert st.status_code == 201 and st.json()["section_name"] == "Class 7-B" and st.json()["has_pin"] is False
    sid = st.json()["id"]
    assert (
        client.post(
            "/api/v1/students", headers=h, json={"admission_no": "N1", "full_name": "X", "section_id": str(a.sec_b)}
        ).status_code
        == 409
    )
    r = client.post(
        f"/api/v1/students/{sid}/guardians",
        headers=h,
        json={"guardian": {"full_name": "Mom", "phone": "9811111111"}, "relation": "MOTHER", "is_primary": True},
    )
    assert r.status_code == 201 and r.json()[0]["phone"] == "+919811111111"
    # Link an existing guardian (parent1) as a second guardian.
    r = client.post(
        f"/api/v1/students/{sid}/guardians", headers=h, json={"guardian_id": str(a.p1), "relation": "FATHER"}
    )
    assert len(r.json()) == 2
    detail = client.get(f"/api/v1/students/{sid}", headers=h).json()
    assert {g["relation"] for g in detail["guardians"]} == {"MOTHER", "FATHER"}
    # Move section
    moved = client.patch(f"/api/v1/students/{sid}", headers=h, json={"section_id": str(a.sec_a)}).json()
    assert moved["section_name"] == "Class 7-A" and moved["roll_no"] == "9"
    # Search + filter + pagination
    page = client.get(f"/api/v1/students?section_id={a.sec_a}&page_size=2", headers=h).json()
    assert page["total"] == 4 and len(page["items"]) == 2
    assert client.get("/api/v1/students?q=new", headers=h).json()["total"] == 1
    # Unlink and soft delete
    assert client.delete(f"/api/v1/students/{sid}/guardians/{a.p1}", headers=h).status_code == 200
    assert client.delete(f"/api/v1/students/{sid}/guardians/{a.p1}", headers=h).status_code == 404
    assert client.delete(f"/api/v1/students/{sid}", headers=h).status_code == 200
    assert client.get(f"/api/v1/students/{sid}", headers=h).status_code == 404


def test_pin_reset_audited_and_works(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    assert client.post(f"/api/v1/students/{a.s2}/pin", headers=a.h("admin"), json={"pin": "9999"}).status_code == 200
    r = client.post(
        "/api/v1/auth/student/login", json={"school_code": "SCHA", "admission_no": "SCHA-S2", "pin": "9999"}
    )
    assert r.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "PIN_RESET", AuditLog.entity_id == a.s2)) is not None


def test_grade_scale_validation(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.a.h("admin")
    scales = client.get("/api/v1/grade-scales", headers=h).json()
    assert scales[0]["name"] == "CBSE 8-point" and len(scales[0]["bands"]) == 8
    bad = client.post(
        "/api/v1/grade-scales",
        headers=h,
        json={
            "name": "Bad",
            "bands": [
                {"grade": "A", "min_percent": 50, "max_percent": 100},
                {"grade": "B", "min_percent": 40, "max_percent": 60},
            ],
        },
    )
    assert bad.status_code == 422
    good = client.post(
        "/api/v1/grade-scales",
        headers=h,
        json={
            "name": "Simple",
            "is_default": True,
            "bands": [
                {"grade": "P", "min_percent": 33, "max_percent": 100},
                {"grade": "F", "min_percent": 0, "max_percent": 32.99},
            ],
        },
    )
    assert good.status_code == 201
    scales = client.get("/api/v1/grade-scales", headers=h).json()
    assert [s["name"] for s in scales if s["is_default"]] == ["Simple"]
    assert client.delete(f"/api/v1/grade-scales/{good.json()['id']}", headers=h).status_code == 422


def test_exam_crud_and_auto_subjects(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    h = a.h("admin")
    e = client.post(
        "/api/v1/exams", headers=h, json={"academic_year_id": str(a.year_id), "name": "Annual", "sequence": 3}
    )
    assert e.status_code == 201
    eid = e.json()["id"]
    # sections have no subject list in this fixture, so add one first
    client.put(f"/api/v1/sections/{a.sec_a}/subjects", headers=h, json={"subject_ids": [str(a.math), str(a.eng)]})
    subs = client.post(f"/api/v1/exams/{eid}/subjects/auto", headers=h, json={"max_marks": 80}).json()
    assert sorted(s["subject_name"] for s in subs) == ["English", "Mathematics"]
    assert all(s["effective_pass_marks"] == "26.40" for s in subs)  # 33% of 80
    bad = client.put(
        f"/api/v1/exams/{eid}/subjects",
        headers=h,
        json={"items": [{"class_id": str(a.class_id), "subject_id": str(a.math), "max_marks": 50, "pass_marks": 60}]},
    )
    assert bad.status_code == 422
    assert client.delete(f"/api/v1/exams/{eid}", headers=h).status_code == 200
    # An exam with marks cannot be deleted.
    from tests.factories import put_marks

    put_marks(client, h, a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 1}])
    assert client.delete(f"/api/v1/exams/{a.e1}", headers=h).status_code == 409


def test_school_profile_and_logo(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.a.h("admin")
    r = client.patch("/api/v1/school", headers=h, json={"address": "1 Main Rd", "pass_percent": 35})
    assert r.json()["address"] == "1 Main Rd" and r.json()["pass_percent"] == "35.00"
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    r = client.post("/api/v1/school/logo", headers=h, files={"file": ("logo.png", png, "image/png")})
    assert r.status_code == 200
    assert client.get("/api/v1/public/schools/scha/logo").content == png
    bad = client.post("/api/v1/school/logo", headers=h, files={"file": ("x.png", b"GIF89a", "image/png")})
    assert bad.status_code == 422
    pub = client.get("/api/v1/public/schools/SCHA").json()
    assert pub["name"] == "School SCHA" and pub["has_logo"] is True
    assert client.get("/api/v1/public/schools/NOPE").status_code == 404


def test_staff_management(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.a.h("admin")
    r = client.post("/api/v1/staff", headers=h, json={"full_name": "VP", "phone": "9822222222", "role": "PRINCIPAL"})
    assert r.status_code == 201
    assert (
        client.post(
            "/api/v1/staff", headers=h, json={"full_name": "X", "phone": "9822222223", "role": "TEACHER"}
        ).status_code
        == 422
    )
    assert client.delete(f"/api/v1/staff/{world.a.roles['admin'].id}", headers=h).status_code == 422
    assert client.delete(f"/api/v1/staff/{r.json()['role_id']}", headers=h).status_code == 200
    assert (
        client.post(
            "/api/v1/staff", headers=world.a.h("principal"), json={"full_name": "X", "phone": "9822222224"}
        ).status_code
        == 403
    )


def test_demo_request(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/public/demo-requests",
        json={"name": "Ravi", "school_name": "ABC School", "phone": "9876543210", "students": 600},
    )
    assert r.status_code == 201


# ------------------------------------------------------------- platform admin
def test_platform_admin_creates_school(client, world) -> None:  # type: ignore[no-untyped-def]
    h = world.platform()
    r = client.post("/api/v1/admin/schools", headers=h, json={"code": "new01", "name": "New School"})
    assert r.status_code == 201 and r.json()["code"] == "NEW01"
    sid = r.json()["id"]
    assert client.post("/api/v1/admin/schools", headers=h, json={"code": "NEW01", "name": "Again"}).status_code == 409
    r = client.post(
        f"/api/v1/admin/schools/{sid}/admins",
        headers=h,
        json={"full_name": "Office", "phone": "9833333333", "role": "SCHOOL_ADMIN"},
    )
    assert r.status_code == 201
    # The new admin can log in and sees the default grade scale and consent text.
    v = client.post("/api/v1/auth/otp/verify", json={"phone": "9833333333", "otp": "123456"}).json()
    tok = client.post("/api/v1/auth/session", json={"ticket": v["ticket"], "role_id": v["roles"][0]["role_id"]})
    ah = {"Authorization": f"Bearer {tok.json()['access_token']}"}
    assert client.get("/api/v1/grade-scales", headers=ah).json()[0]["is_default"] is True
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "SCHOOL_CREATE")) is not None
    assert {s["code"] for s in client.get("/api/v1/admin/schools", headers=h).json()} == {"SCHA", "SCHB", "NEW01"}
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "PLATFORM_ADMIN_ACCESS")) is not None
    _ = GradeScale


def test_deactivated_school_cannot_log_in(client, world) -> None:  # type: ignore[no-untyped-def]
    r = client.patch(f"/api/v1/admin/schools/{world.a.school_id}", headers=world.platform(), json={"is_active": False})
    assert r.json()["is_active"] is False
    v = client.post("/api/v1/auth/otp/verify", json={"phone": "9800000002", "otp": "123456"}).json()
    assert v["roles"] == []


def test_only_platform_admin_on_admin_routes(client, world) -> None:  # type: ignore[no-untyped-def]
    for who in ("admin", "principal", "teacher1", "parent1"):
        assert client.get("/api/v1/admin/schools", headers=world.a.h(who)).status_code == 403
    # Platform admin has no school role, so school-scoped endpoints refuse it.
    assert client.get("/api/v1/students", headers=world.platform()).status_code == 403
