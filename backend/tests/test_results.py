"""Results, progress and visibility. Numbers are hand-calculated (DESIGN.md §8).

Fixture marks, Unit Test 1 (all subjects max 100, pass 33):
  S1: Maths 80, Science AB, English EX  -> 80 / 200 = 40.00% -> D, fails Science -> not passed
  S2: Maths 90, Science 85, English 70  -> 245 / 300 = 81.67% -> A2, passed
  S3: Maths 20, Science 30, English 95  -> 145 / 300 = 48.33% -> C2, 2 fails
Ranks in 7-A: S2=1, S3=2, S1=3.
Half-Yearly: S1 Maths 50, Science 50, English 50 -> 50.00% (C2)
"""

import pytest

from app.core.db import SessionLocal, set_tenant
from tests.factories import put_marks


@pytest.fixture
def marked(client, world):  # type: ignore[no-untyped-def]
    a = world.a
    h = a.h("admin")
    put_marks(
        client,
        h,
        a.e1_math,
        a.sec_a,
        [{"student_id": a.s1, "marks": 80}, {"student_id": a.s2, "marks": 90}, {"student_id": a.s3, "marks": 20}],
    )
    put_marks(
        client,
        h,
        a.e1_sci,
        a.sec_a,
        [
            {"student_id": a.s1, "status": "ABSENT"},
            {"student_id": a.s2, "marks": 85},
            {"student_id": a.s3, "marks": 30},
        ],
    )
    put_marks(
        client,
        h,
        a.e1_eng,
        a.sec_a,
        [
            {"student_id": a.s1, "status": "EXEMPT"},
            {"student_id": a.s2, "marks": 70},
            {"student_id": a.s3, "marks": 95},
        ],
    )
    for es in (a.e2_math, a.e2_sci, a.e2_eng):
        put_marks(client, h, es, a.sec_a, [{"student_id": a.s1, "marks": 50}])
    put_marks(client, h, a.e1_math, a.sec_b, [{"student_id": a.s4, "marks": 60}])
    client.post(f"/api/v1/exams/{a.e1}/publications", headers=a.h("principal"), json={})  # whole exam
    return world


def _get(client, w, who, url):  # type: ignore[no-untyped-def]
    return client.get(url, headers=w.h(who))


def test_results_numbers_match_hand_calculation(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    expected = {
        a.s1: ("40.00", "D", False, 3, 1),
        a.s2: ("81.67", "A2", True, 1, 0),
        a.s3: ("48.33", "C2", False, 2, 2),
    }
    for sid, (pct, grade, passed, rank, failed) in expected.items():
        rows = _get(client, a, "principal", f"/api/v1/students/{sid}/results").json()
        ut1 = next(r for r in rows if r["exam_id"] == str(a.e1))
        assert (ut1["percentage"], ut1["grade"], ut1["passed"], ut1["rank"], ut1["subjects_failed"]) == (
            pct,
            grade,
            passed,
            rank,
            failed,
        ), sid
        assert ut1["section_size"] == 3
    s1 = next(
        r for r in _get(client, a, "principal", f"/api/v1/students/{a.s1}/results").json() if r["exam_id"] == str(a.e1)
    )
    assert (s1["total_obtained"], s1["total_max"]) == ("80.00", "200.00")


def test_exam_detail_subjects(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    d = _get(client, a, "parent1", f"/api/v1/students/{a.s1}/results/{a.e1}").json()
    subj = {s["subject_name"]: s for s in d["subjects"]}
    assert subj["Mathematics"]["marks"] == "80.00" and subj["Mathematics"]["grade"] == "B1"
    assert subj["Mathematics"]["passed"] is True and subj["Mathematics"]["pass_marks"] == "33.00"
    assert subj["Science"]["status"] == "ABSENT" and subj["Science"]["passed"] is False
    assert subj["English"]["status"] == "EXEMPT" and subj["English"]["passed"] is None
    assert d["student_name"] == "Asha SCHA"


def test_unpublished_marks_are_invisible_to_parent_and_student(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    for who in ("parent1", "student_s1"):
        rows = _get(client, a, who, f"/api/v1/students/{a.s1}/results").json()
        assert [r["exam_name"] for r in rows] == ["Unit Test 1"]  # Half-Yearly is draft
        assert _get(client, a, who, f"/api/v1/students/{a.s1}/results/{a.e2}").status_code == 404
        progress = _get(client, a, who, f"/api/v1/students/{a.s1}/progress").json()
        assert [p["exam_name"] for p in progress["overall"]] == ["Unit Test 1"]
        assert all(len(s["points"]) == 1 for s in progress["subjects"])
    # Staff do see the draft exam.
    rows = _get(client, a, "principal", f"/api/v1/students/{a.s1}/results").json()
    assert {r["exam_name"]: r["published"] for r in rows} == {"Unit Test 1": True, "Half-Yearly": False}


def test_unpublish_hides_again(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    client.request("DELETE", f"/api/v1/exams/{a.e1}/publications", headers=a.h("principal"), json={})
    assert _get(client, a, "parent1", f"/api/v1/students/{a.s1}/results").json() == []


def test_parent_idor_other_child_404(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    for url in (
        f"/api/v1/students/{a.s2}/results",
        f"/api/v1/students/{a.s2}/results/{a.e1}",
        f"/api/v1/students/{a.s2}/progress",
        f"/api/v1/students/{a.s2}/report-cards/{a.e1}.pdf",
    ):
        assert _get(client, a, "parent1", url).status_code == 404, url
        assert _get(client, a, "student_s1", url).status_code == 404, url
    # Parent and student cannot reach staff lists either.
    for url in (
        "/api/v1/students",
        f"/api/v1/students/{a.s1}",
        "/api/v1/teachers",
        f"/api/v1/dashboard/summary?exam_id={a.e1}",
    ):
        assert _get(client, a, "parent1", url).status_code == 403, url
        assert _get(client, a, "student_s1", url).status_code == 403, url


def test_teacher_sees_only_students_they_teach(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    assert _get(client, a, "teacher1", f"/api/v1/students/{a.s1}/results").status_code == 200
    assert _get(client, a, "teacher1", f"/api/v1/students/{a.s4}/results").status_code == 404  # 7-B


def test_children_lists_only_linked(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    kids = _get(client, a, "parent1", "/api/v1/children").json()
    assert [k["student_id"] for k in kids] == [str(a.s1)]
    assert kids[0]["section_name"] == "Class 7-A" and kids[0]["relation"] == "FATHER"


def test_rank_hidden_when_school_disables_it(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    client.patch("/api/v1/school", headers=a.h("admin"), json={"show_rank": False})
    assert _get(client, a, "parent1", f"/api/v1/students/{a.s1}/results").json()[0]["rank"] is None
    assert _get(client, a, "principal", f"/api/v1/students/{a.s1}/results").json()[0]["rank"] is not None


def test_progress_series(client, marked) -> None:  # type: ignore[no-untyped-def]
    a = marked.a
    p = _get(client, a, "principal", f"/api/v1/students/{a.s1}/progress").json()
    assert [(x["exam_name"], x["percentage"]) for x in p["overall"]] == [
        ("Unit Test 1", "40.00"),
        ("Half-Yearly", "50.00"),
    ]
    maths = next(s for s in p["subjects"] if s["subject_name"] == "Mathematics")
    assert [x["percentage"] for x in maths["points"]] == ["80.00", "50.00"]
    english = next(s for s in p["subjects"] if s["subject_name"] == "English")
    assert english["points"][0]["percentage"] is None  # exempt


def test_consent_required_before_any_child_data(client, marked, owner_engine) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    a = marked.a
    with owner_engine.begin() as conn:
        conn.execute(text("DELETE FROM consents"))
    for url in ("/api/v1/children", f"/api/v1/students/{a.s1}/results"):
        r = _get(client, a, "parent1", url)
        assert r.status_code == 403 and r.json()["error"]["code"] == "CONSENT_REQUIRED"
    assert _get(client, a, "parent1", "/api/v1/me").json()["consent_required"] is True
    c = _get(client, a, "parent1", "/api/v1/consent/current").json()
    assert c["version"] == 1 and c["accepted"] is False
    assert client.post("/api/v1/consent/accept", headers=a.h("parent1"), json={"version": 99}).status_code == 404
    assert client.post("/api/v1/consent/accept", headers=a.h("parent1"), json={"version": 1}).status_code == 200
    assert _get(client, a, "parent1", "/api/v1/children").status_code == 200
    with SessionLocal() as db:
        set_tenant(db, a.school_id)
        n = db.execute(text("SELECT count(*) FROM consents WHERE guardian_id = :g"), {"g": a.p1}).scalar()
        assert n == 1


def test_report_card_html_and_pdf(client, marked) -> None:  # type: ignore[no-untyped-def]
    from app.services import pdf
    from tests.factories import _ctx_for

    a = marked.a
    with SessionLocal() as db:
        set_tenant(db, a.school_id)
        html = pdf.render_html(_ctx_for(db, a.roles["parent1"]), a.s1, a.e1)
    assert (
        "Asha SCHA" in html
        and "UNIT TEST 1" in html
        and "40%" in html
        and ">AB<" in html.replace("\n", "").replace(" ", "")
    )
    r = _get(client, a, "parent1", f"/api/v1/students/{a.s1}/report-cards/{a.e1}.pdf")
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        assert r.status_code == 503
        pytest.skip("WeasyPrint system libraries not installed; PDF bytes are tested in Docker/CI")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    # Not published for Half-Yearly -> not available to the parent.
    assert _get(client, a, "parent1", f"/api/v1/students/{a.s1}/report-cards/{a.e2}.pdf").status_code == 404
