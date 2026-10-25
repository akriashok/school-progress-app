"""RLS policies: treat an empty app.school_id as "no tenant" (no rows) instead of a cast error.

Revision ID: 0003_rls_nullif
Revises: 0002_demo_requests
Create Date: 2026-10-25
"""

from alembic import op

revision = "0003_rls_nullif"
down_revision = "0002_demo_requests"
branch_labels = None
depends_on = None

TABLES = [
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

NEW = "school_id = NULLIF(current_setting('app.school_id', true), '')::uuid"
OLD = "school_id = current_setting('app.school_id', true)::uuid"


def _apply(expr: str) -> None:
    for t in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"CREATE POLICY tenant_isolation ON {t} USING ({expr}) WITH CHECK ({expr})")


def upgrade() -> None:
    _apply(NEW)


def downgrade() -> None:
    _apply(OLD)
