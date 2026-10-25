from sqlalchemy import select

from app.core.db import SessionLocal, set_tenant
from app.models import AuditLog, Mark
from tests.factories import put_marks


def _grid(client, w, who, es, sec):  # type: ignore[no-untyped-def]
    return client.get(f"/api/v1/marks?exam_subject_id={es}&section_id={sec}", headers=w.h(who))


def test_teacher_happy_path_and_audit(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    g = _grid(client, a, "teacher1", a.e1_math, a.sec_a)
    assert g.status_code == 200
    body = g.json()
    assert [r["admission_no"] for r in body["rows"]] == ["SCHA-S1", "SCHA-S2", "SCHA-S3"]
    assert body["can_edit"] and not body["published"] and body["max_marks"] == "100.00"

    r = put_marks(
        client,
        a.h("teacher1"),
        a.e1_math,
        a.sec_a,
        [
            {"student_id": a.s1, "marks": 78.5},
            {"student_id": a.s2, "status": "ABSENT"},
            {"student_id": a.s3, "status": "EXEMPT"},
        ],
    )
    assert r.status_code == 200 and r.json() == {"created": 3, "updated": 0, "unchanged": 0}
    # Same values again: nothing changes, no new audit rows.
    r = put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 78.5}])
    assert r.json() == {"created": 0, "updated": 0, "unchanged": 1}
    r = put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 80}])
    assert r.json()["updated"] == 1

    rows = {x["student_id"]: x for x in _grid(client, a, "teacher1", a.e1_math, a.sec_a).json()["rows"]}
    assert rows[str(a.s1)]["marks"] == "80.00" and rows[str(a.s1)]["version"] == 2
    assert rows[str(a.s2)]["status"] == "ABSENT" and rows[str(a.s2)]["marks"] is None
    assert rows[str(a.s3)]["status"] == "EXEMPT"

    with SessionLocal() as db:
        set_tenant(db, a.school_id)
        logs = db.scalars(
            select(AuditLog).where(AuditLog.action.in_(["MARK_CREATE", "MARK_UPDATE"])).order_by(AuditLog.id)
        ).all()
    assert [x.action for x in logs] == ["MARK_CREATE"] * 3 + ["MARK_UPDATE"]
    assert logs[-1].old_value["marks"] == "78.50" and logs[-1].new_value["marks"] == "80.00"
    assert logs[-1].user_id == a.roles["teacher1"].user_id


def test_marks_above_max_negative_and_decimals_rejected(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    for bad in (105, -1, 50.123):
        r = put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": bad}])
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "MARKS_INVALID"
    r = put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 105}])
    assert "105 > max 100" in r.json()["error"]["details"][0]["message"]
    # Nothing saved when any row is invalid
    r = put_marks(
        client,
        a.h("teacher1"),
        a.e1_math,
        a.sec_a,
        [{"student_id": a.s1, "marks": 50}, {"student_id": a.s2, "marks": 101}],
    )
    assert r.status_code == 422
    with SessionLocal() as db:
        set_tenant(db, a.school_id)
        assert db.scalar(select(Mark)) is None


def test_student_from_other_section_rejected(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    r = put_marks(client, a.h("admin"), a.e1_math, a.sec_a, [{"student_id": a.s4, "marks": 10}])
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["message"] == "student is not in this section"


def test_teacher_of_other_section_or_subject_gets_403(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    # teacher2 teaches 7-B maths and 7-A English, not 7-A maths
    assert _grid(client, a, "teacher2", a.e1_math, a.sec_a).status_code == 403
    r = put_marks(client, a.h("teacher2"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 10}])
    assert r.status_code == 403
    # teacher1 teaches 7-A maths, not 7-B maths
    assert _grid(client, a, "teacher1", a.e1_math, a.sec_b).status_code == 403
    assert _grid(client, a, "teacher2", a.e1_math, a.sec_b).status_code == 200


def test_parent_and_student_get_403(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    for who in ("parent1", "student_s1"):
        assert _grid(client, a, who, a.e1_math, a.sec_a).status_code == 403
        r = put_marks(client, a.h(who), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 100}])
        assert r.status_code == 403


def test_school_b_token_gets_404(client, world) -> None:  # type: ignore[no-untyped-def]
    a, b = world.a, world.b
    assert _grid(client, b, "admin", a.e1_math, a.sec_a).status_code == 404
    r = put_marks(client, b.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 10}])
    assert r.status_code == 404


def test_submit_requires_all_marks(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    body = {"exam_subject_id": str(a.e1_math), "section_id": str(a.sec_a)}
    put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 10}])
    r = client.post("/api/v1/marks/submit", headers=a.h("teacher1"), json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "MARKS_INCOMPLETE"
    put_marks(
        client,
        a.h("teacher1"),
        a.e1_math,
        a.sec_a,
        [{"student_id": a.s2, "marks": 20}, {"student_id": a.s3, "status": "ABSENT"}],
    )
    r = client.post("/api/v1/marks/submit", headers=a.h("teacher1"), json=body)
    assert r.status_code == 200 and r.json()["status"] == "SUBMITTED"

    status = client.get(f"/api/v1/exams/{a.e1}/status", headers=a.h("principal")).json()
    row = next(x for x in status["rows"] if x["exam_subject_id"] == str(a.e1_math) and x["section_id"] == str(a.sec_a))
    assert row["status"] == "SUBMITTED" and row["entered"] == 3 and row["students"] == 3
    assert row["teachers"] == ["Teacher One SCHA"]
    pending = [x for x in status["rows"] if x["status"] != "SUBMITTED"]
    assert status["submitted"] == 1 and len(pending) == status["total"] - 1
    assert client.get(f"/api/v1/exams/{a.e1}/status", headers=a.h("teacher1")).status_code == 403


def test_publish_locks_teacher_and_requires_reason_for_principal(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 40}])
    r = client.post(
        f"/api/v1/exams/{a.e1}/publications", headers=a.h("principal"), json={"section_ids": [str(a.sec_a)]}
    )
    assert r.status_code == 200 and [p["section_id"] for p in r.json()] == [str(a.sec_a)]

    r = put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 41}])
    assert r.status_code == 403 and r.json()["error"]["code"] == "RESULTS_PUBLISHED"
    assert _grid(client, a, "teacher1", a.e1_math, a.sec_a).json()["can_edit"] is False

    r = put_marks(client, a.h("principal"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 41}])
    assert r.status_code == 422 and r.json()["error"]["code"] == "REASON_REQUIRED"
    r = put_marks(
        client, a.h("principal"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 41}], reason="Re-totalling error"
    )
    assert r.status_code == 200
    with SessionLocal() as db:
        set_tenant(db, a.school_id)
        log = db.scalar(select(AuditLog).where(AuditLog.action == "MARK_UPDATE"))
        assert log is not None and log.reason == "Re-totalling error"
        assert db.scalar(select(AuditLog).where(AuditLog.action == "RESULT_PUBLISH")) is not None

    # Unpublish unlocks the teacher again.
    r = client.request(
        "DELETE", f"/api/v1/exams/{a.e1}/publications", headers=a.h("principal"), json={"section_ids": [str(a.sec_a)]}
    )
    assert r.status_code == 200 and r.json() == []
    r = put_marks(client, a.h("teacher1"), a.e1_math, a.sec_a, [{"student_id": a.s1, "marks": 42}])
    assert r.status_code == 200


def test_only_managers_publish(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    for who in ("teacher1", "parent1", "student_s1"):
        assert client.post(f"/api/v1/exams/{a.e1}/publications", headers=a.h(who), json={}).status_code == 403


def test_publish_sends_push_to_linked_families(client, world) -> None:  # type: ignore[no-untyped-def]
    from app.services import notifications

    a = world.a
    for who, token in (
        ("parent1", "token-parent-one-a"),
        ("student_s4", "token-student-four"),
        ("parent1", "token-parent-one-b"),
    ):
        assert client.post("/api/v1/devices", headers=a.h(who), json={"fcm_token": token}).status_code == 201
    client.post(f"/api/v1/exams/{a.e1}/publications", headers=a.h("principal"), json={"section_ids": [str(a.sec_a)]})
    sender = notifications.get_sender()
    assert isinstance(sender, notifications.LogSender)
    assert len(sender.sent) == 1
    assert sorted(sender.sent[0]["tokens"]) == ["token-parent-one-a", "token-parent-one-b"]  # type: ignore[arg-type]
    # Publishing the same section again does not notify twice.
    client.post(f"/api/v1/exams/{a.e1}/publications", headers=a.h("principal"), json={"section_ids": [str(a.sec_a)]})
    assert len(sender.sent) == 1


def test_scope_mismatch_rejected(client, world) -> None:  # type: ignore[no-untyped-def]
    # An exam subject for another class can't be used with this section.
    a = world.a
    cls = client.post("/api/v1/classes", headers=a.h("admin"), json={"name": "8", "sort_order": 8}).json()
    es = client.put(
        f"/api/v1/exams/{a.e1}/subjects",
        headers=a.h("admin"),
        json={"items": [{"class_id": cls["id"], "subject_id": str(a.math), "max_marks": 50}]},
    ).json()
    es8 = next(x for x in es if x["class_id"] == cls["id"])
    r = _grid(client, a, "admin", es8["id"], a.sec_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "SCOPE_MISMATCH"


def test_my_assignments(client, world) -> None:  # type: ignore[no-untyped-def]
    a = world.a
    rows = client.get("/api/v1/teacher/my-assignments", headers=a.h("teacher1")).json()
    assert sorted(r["subject_name"] for r in rows) == ["Mathematics", "Science"]
    assert all(r["section_name"] == "Class 7-A" and r["student_count"] == 3 for r in rows)
    assert client.get("/api/v1/teacher/my-assignments", headers=a.h("principal")).status_code == 403
