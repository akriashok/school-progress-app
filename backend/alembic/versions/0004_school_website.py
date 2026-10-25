"""schools.website: content for each school's public website (hero, about, facilities, gallery...).

Revision ID: 0004_school_website
Revises: 0003_rls_nullif
Create Date: 2026-10-25
"""

from alembic import op

revision = "0004_school_website"
down_revision = "0003_rls_nullif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE schools ADD COLUMN website jsonb NOT NULL DEFAULT '{}'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE schools DROP COLUMN website")
