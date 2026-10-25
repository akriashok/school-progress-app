"""Test setup: a dedicated database, migrated once, truncated before every test.

The app connects as the non-owner role (app_user), exactly like production, so
Row-Level Security is exercised by every test.
"""

import os

os.environ.update(
    {
        "ENV": "test",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL", "postgresql+psycopg://app_user:app_user_dev@localhost:5433/vidyatrack_test"
        ),
        "MIGRATION_DATABASE_URL": os.environ.get(
            "TEST_MIGRATION_DATABASE_URL",
            "postgresql+psycopg://vidya_owner:vidya_owner_dev@localhost:5433/vidyatrack_test",
        ),
        "DEV_OTP_ENABLED": "true",
        "REDIS_URL": "",
        "SMS_BACKEND": "console",
        "PUSH_BACKEND": "log",
        "STORAGE_BACKEND": "local",
        "JWT_SECRET": "test-secret-that-is-long-enough-for-hs256-signing-000",
    }
)

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.ratelimit import get_limiter  # noqa: E402
from app.services import notifications, storage  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrate() -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def owner_engine():  # type: ignore[no-untyped-def]
    engine = create_engine(get_settings().migration_database_url)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean(owner_engine, tmp_path) -> Iterator[None]:  # type: ignore[no-untyped-def]
    with owner_engine.begin() as conn:
        tables = (
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
            )
            .scalars()
            .all()
        )
        conn.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"))
    get_limiter().reset()
    storage.set_storage(storage.LocalStorage(str(tmp_path / "storage")))
    sender = notifications.LogSender()
    notifications.set_sender(sender)
    yield


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def world():  # type: ignore[no-untyped-def]
    from tests.factories import build_world

    return build_world()
