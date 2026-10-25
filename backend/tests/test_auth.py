from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.config import Settings, get_settings
from app.core.db import SessionLocal
from app.models import AuditLog, OtpCode, RefreshToken
from app.services import sms

PRINCIPAL_A = "+919800000002"


@pytest.fixture
def captured_otps(monkeypatch):  # type: ignore[no-untyped-def]
    sent: dict[str, str] = {}
    monkeypatch.setattr(sms, "send_otp", lambda phone, code: sent.__setitem__(phone, code))
    return sent


@pytest.fixture
def real_otp_only(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "dev_otp_enabled", False)


def _verify(client, phone: str, otp: str):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})


def _login(client, phone: str, client_type: str = "app"):  # type: ignore[no-untyped-def]
    d = _verify(client, phone, "123456").json()
    return client.post(
        "/api/v1/auth/session", json={"ticket": d["ticket"], "role_id": d["roles"][0]["role_id"], "client": client_type}
    )


# ------------------------------------------------------------------- OTP
def test_otp_request_is_always_200(client, world, captured_otps):  # type: ignore[no-untyped-def]
    assert client.post("/api/v1/auth/otp/request", json={"phone": "9800000002"}).status_code == 200
    assert client.post("/api/v1/auth/otp/request", json={"phone": "9111111111"}).status_code == 200
    assert list(captured_otps) == [PRINCIPAL_A]  # only the registered number gets an SMS


def test_otp_is_stored_hashed(client, world, captured_otps):  # type: ignore[no-untyped-def]
    client.post("/api/v1/auth/otp/request", json={"phone": PRINCIPAL_A})
    with SessionLocal() as db:
        row = db.scalar(select(OtpCode))
    assert row is not None and captured_otps[PRINCIPAL_A] not in row.code_hash


def test_real_otp_flow(client, world, captured_otps, real_otp_only):  # type: ignore[no-untyped-def]
    client.post("/api/v1/auth/otp/request", json={"phone": PRINCIPAL_A})
    r = _verify(client, PRINCIPAL_A, captured_otps[PRINCIPAL_A])
    assert r.status_code == 200
    roles = r.json()["roles"]
    assert [x["role"] for x in roles] == ["PRINCIPAL"]
    # OTP is single use
    assert _verify(client, PRINCIPAL_A, captured_otps[PRINCIPAL_A]).status_code == 401


def test_wrong_otp_and_attempt_limit(client, world, captured_otps, real_otp_only):  # type: ignore[no-untyped-def]
    client.post("/api/v1/auth/otp/request", json={"phone": PRINCIPAL_A})
    good = captured_otps[PRINCIPAL_A]
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(5):
        r = _verify(client, PRINCIPAL_A, wrong)
        assert r.status_code == 401 and r.json()["error"]["code"] == "OTP_INVALID"
    r = _verify(client, PRINCIPAL_A, good)
    assert r.status_code == 401 and r.json()["error"]["code"] == "OTP_LOCKED"


def test_expired_otp(client, world, captured_otps, real_otp_only):  # type: ignore[no-untyped-def]
    client.post("/api/v1/auth/otp/request", json={"phone": PRINCIPAL_A})
    with SessionLocal() as db:
        db.execute(update(OtpCode).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        db.commit()
    assert _verify(client, PRINCIPAL_A, captured_otps[PRINCIPAL_A]).status_code == 401


def test_otp_rate_limit_per_phone(client, world, captured_otps):  # type: ignore[no-untyped-def]
    for _ in range(3):
        assert client.post("/api/v1/auth/otp/request", json={"phone": PRINCIPAL_A}).status_code == 200
    r = client.post("/api/v1/auth/otp/request", json={"phone": PRINCIPAL_A})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_otp_rate_limit_per_ip(client, world, captured_otps):  # type: ignore[no-untyped-def]
    for i in range(20):
        assert client.post("/api/v1/auth/otp/request", json={"phone": f"98765{i:05d}"}).status_code == 200
    assert client.post("/api/v1/auth/otp/request", json={"phone": "9876599999"}).status_code == 429


# --------------------------------------------------------------- sessions
def test_session_and_me(client, world):  # type: ignore[no-untyped-def]
    r = _login(client, PRINCIPAL_A)
    assert r.status_code == 200 and r.json()["refresh_token"]
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "PRINCIPAL" and me["school_code"] == "SCHA"
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "LOGIN")) is not None


def test_cannot_pick_someone_elses_role(client, world):  # type: ignore[no-untyped-def]
    ticket = _verify(client, PRINCIPAL_A, "123456").json()["ticket"]
    other = str(world.b.roles["principal"].id)
    r = client.post("/api/v1/auth/session", json={"ticket": ticket, "role_id": other})
    assert r.status_code == 403


def test_multi_role_user_sees_all_roles(client, world):  # type: ignore[no-untyped-def]
    # Teacher One of school A is also a parent in school B (same phone).
    from app.core.db import set_tenant
    from app.schemas.setup import GuardianIn
    from app.services import people
    from tests.factories import _ctx_for

    with SessionLocal() as db:
        set_tenant(db, world.b.school_id)
        people.upsert_guardian(
            _ctx_for(db, world.b.roles["admin"]), GuardianIn(full_name="Teacher One", phone="+919800000011")
        )
        db.commit()
    roles = _verify(client, "+919800000011", "123456").json()["roles"]
    assert sorted((x["role"], x["school_code"]) for x in roles) == [("PARENT", "SCHB"), ("TEACHER", "SCHA")]


def test_refresh_rotation_and_reuse_detection(client, world):  # type: ignore[no-untyped-def]
    first = _login(client, PRINCIPAL_A).json()["refresh_token"]
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert r.status_code == 200
    second = r.json()["refresh_token"]
    assert second != first
    # Reusing the rotated token revokes the whole family.
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert r.status_code == 401 and r.json()["error"]["code"] == "REFRESH_REUSED"
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": second}).status_code == 401


def test_logout_revokes_refresh_token(client, world):  # type: ignore[no-untyped-def]
    token = _login(client, PRINCIPAL_A).json()["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": token}).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_expired_refresh_token(client, world):  # type: ignore[no-untyped-def]
    token = _login(client, PRINCIPAL_A).json()["refresh_token"]
    with SessionLocal() as db:
        db.execute(update(RefreshToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        db.commit()
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_web_client_gets_httponly_cookie(client, world):  # type: ignore[no-untyped-def]
    r = _login(client, PRINCIPAL_A, "web")
    assert r.json()["refresh_token"] is None
    cookie = r.headers["set-cookie"]
    assert "vt_refresh=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    r = client.post("/api/v1/auth/refresh")  # TestClient resends the cookie
    assert r.status_code == 200 and r.json()["access_token"]


def test_invalid_and_missing_tokens(client, world):  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/me").status_code == 401
    r = client.get("/api/v1/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_INVALID"


def test_switch_role(client, world):  # type: ignore[no-untyped-def]
    from app.core.db import set_tenant
    from app.schemas.setup import GuardianIn
    from app.services import people
    from tests.factories import _ctx_for

    with SessionLocal() as db:
        set_tenant(db, world.a.school_id)
        people.upsert_guardian(
            _ctx_for(db, world.a.roles["admin"]), GuardianIn(full_name="Teacher One", phone="+919800000011")
        )
        db.commit()
    tokens = _login(client, "+919800000011").json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/api/v1/me", headers=h).json()
    target = me["other_roles"][0]
    r = client.post("/api/v1/auth/switch", headers=h, json={"role_id": target["role_id"]})
    assert r.status_code == 200
    me2 = client.get("/api/v1/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me2["role"] == target["role"]
    # A role that is not yours is refused.
    r = client.post("/api/v1/auth/switch", headers=h, json={"role_id": str(world.b.roles["admin"].id)})
    assert r.status_code == 403


# --------------------------------------------------------- student login
def _student(client, code="SCHA", adm="SCHA-S1", pin="4321"):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/student/login", json={"school_code": code, "admission_no": adm, "pin": pin})


def test_student_login(client, world):  # type: ignore[no-untyped-def]
    r = _student(client, code="scha")
    assert r.status_code == 200
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "STUDENT" and me["student_id"] == str(world.a.s1)


def test_student_login_wrong_school_or_pin(client, world):  # type: ignore[no-untyped-def]
    assert _student(client, pin="0000").status_code == 401
    assert _student(client, code="SCHB").status_code == 401  # admission no belongs to school A
    assert _student(client, code="NOPE").status_code == 401


def test_student_lockout_after_5_failures(client, world):  # type: ignore[no-untyped-def]
    for _ in range(5):
        assert _student(client, pin="0000").status_code == 401
    r = _student(client)  # correct PIN, but locked
    assert r.status_code == 401 and r.json()["error"]["code"] == "STUDENT_LOCKED"


# ------------------------------------------------------------ config
def test_dev_otp_cannot_be_enabled_in_production() -> None:
    with pytest.raises(ValueError, match="DEV_OTP_ENABLED"):
        Settings(env="production", dev_otp_enabled=True, jwt_secret="x" * 40, sms_backend="http", cookie_secure=True)


def test_production_requires_strong_secret_and_real_sms() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(
            env="production",
            dev_otp_enabled=False,
            jwt_secret="dev-only-insecure-secret-change-me",
            sms_backend="http",
            cookie_secure=True,
        )
    with pytest.raises(ValueError, match="SMS_BACKEND"):
        Settings(
            env="production", dev_otp_enabled=False, jwt_secret="x" * 40, sms_backend="console", cookie_secure=True
        )
    ok = Settings(env="production", dev_otp_enabled=False, jwt_secret="x" * 40, sms_backend="http", cookie_secure=True)
    assert not ok.dev_otp_enabled


def test_dev_otp_ignored_outside_dev(client, world, monkeypatch):  # type: ignore[no-untyped-def]
    # Even if the flag were somehow set, verify_otp also checks the environment.
    monkeypatch.setattr(get_settings(), "env", "production")
    assert _verify(client, PRINCIPAL_A, "123456").status_code == 401


def test_health(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/health").json() == {"status": "ok"}
