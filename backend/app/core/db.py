"""Database engine and sessions.

Tenant isolation, layer 2 (defense in depth): every transaction opened by a
tenant-scoped session runs ``set_config('app.school_id', <id>, true)`` so the
Postgres RLS policies only expose that school's rows. Layer 1 is the explicit
``school_id`` filter in every service query.
"""

from collections.abc import Iterator
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

TENANT_KEY = "school_id"


@event.listens_for(Session, "after_begin")
def _apply_tenant(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
    school_id = session.info.get(TENANT_KEY)
    # Empty string means "no tenant": RLS then matches nothing on school tables.
    connection.execute(
        text("SELECT set_config('app.school_id', :sid, true)"),
        {"sid": str(school_id) if school_id else ""},
    )


def set_tenant(session: Session, school_id: UUID | None) -> None:
    """Scope the session (current and future transactions) to one school."""
    session.info[TENANT_KEY] = school_id
    if session.in_transaction():
        session.execute(
            text("SELECT set_config('app.school_id', :sid, true)"),
            {"sid": str(school_id) if school_id else ""},
        )


def session_scope(school_id: UUID | None = None) -> Iterator[Session]:
    session = SessionLocal()
    session.info[TENANT_KEY] = school_id
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def tenant_school_id(session: Session) -> Any:
    return session.info.get(TENANT_KEY)
