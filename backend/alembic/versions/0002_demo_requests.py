"""demo_requests: 'Book a demo' leads from the public landing page.

Revision ID: 0002_demo_requests
Revises: 0001_initial
Create Date: 2026-10-25
"""

from alembic import op

from app.core.config import get_settings

revision = "0002_demo_requests"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE demo_requests (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name        varchar(150) NOT NULL,
            school_name varchar(200) NOT NULL,
            phone       varchar(15) NOT NULL,
            city        varchar(80),
            students    integer,
            message     text,
            created_at  timestamptz NOT NULL DEFAULT now()
        )
    """)
    role = get_settings().app_db_role
    # The public form may only insert; leads are read by the sales team, not the API.
    op.execute(f"GRANT INSERT ON demo_requests TO {role}")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_requests")
