"""Initial schema: all v1 tables, results view, RLS policies, API-role grants.

Generated from db/schema.sql (v1.0). This migration is immutable; later model
changes go in new revisions (and db/schema.sql is updated alongside).

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-25
"""

from alembic import op

from app.core.config import get_settings

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = r"""
-- =====================================================================
-- School Progress App: reference schema (PostgreSQL 16)
-- Version 1.0 (draft), 25 Oct 2026
--
-- This file is the REFERENCE design. Once the backend exists, Alembic
-- migrations become the source of truth; keep this file in sync.
--
-- Conventions
--   * UUID primary keys (gen_random_uuid()).
--   * Every school-owned table has school_id NOT NULL + an index on it.
--   * created_at / updated_at on every table; soft delete via deleted_at
--     for people. Marks are never hard-deleted.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;

-- ---------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------
CREATE TYPE role_type          AS ENUM ('PLATFORM_ADMIN','SCHOOL_ADMIN','PRINCIPAL','TEACHER','PARENT','STUDENT');
CREATE TYPE gender_type        AS ENUM ('MALE','FEMALE','OTHER');
CREATE TYPE guardian_relation  AS ENUM ('FATHER','MOTHER','GUARDIAN');
CREATE TYPE mark_status        AS ENUM ('PRESENT','ABSENT','EXEMPT');
CREATE TYPE submission_status  AS ENUM ('DRAFT','SUBMITTED');
CREATE TYPE import_type        AS ENUM ('STUDENTS','TEACHERS','MARKS');
CREATE TYPE import_status      AS ENUM ('UPLOADED','VALIDATING','READY','COMMITTING','COMMITTED','FAILED');

-- ---------------------------------------------------------------------
-- Tenancy
-- ---------------------------------------------------------------------
CREATE TABLE schools (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code            varchar(12) NOT NULL UNIQUE,        -- used by students to log in, e.g. 'SVHS01'
    name            varchar(200) NOT NULL,
    board           varchar(30),                        -- CBSE / ICSE / STATE
    address         text,
    city            varchar(80),
    state           varchar(80),
    pincode         varchar(10),
    phone           varchar(15),
    email           citext,
    logo_url        text,
    show_rank       boolean NOT NULL DEFAULT true,
    pass_percent    numeric(5,2) NOT NULL DEFAULT 33.00,
    modules         jsonb NOT NULL DEFAULT '{}'::jsonb,  -- future: {"attendance":true}
    branding        jsonb NOT NULL DEFAULT '{}'::jsonb,  -- future: white-label
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Identity: one user per real person (phone); roles are per school
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone           varchar(15) UNIQUE,                 -- E.164, e.g. +919876543210; NULL for student-only logins
    full_name       varchar(150) NOT NULL,
    email           citext,
    is_active       boolean NOT NULL DEFAULT true,
    last_login_at   timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE otp_codes (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone           varchar(15) NOT NULL,
    code_hash       text NOT NULL,
    expires_at      timestamptz NOT NULL,
    attempts        smallint NOT NULL DEFAULT 0,
    consumed_at     timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_otp_phone_created ON otp_codes (phone, created_at DESC);

CREATE TABLE refresh_tokens (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_role_id    uuid NOT NULL,                      -- FK added after user_roles
    token_hash      text NOT NULL UNIQUE,
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz,
    replaced_by     uuid,
    user_agent      text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Academic structure
-- ---------------------------------------------------------------------
CREATE TABLE academic_years (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    name            varchar(20) NOT NULL,               -- '2026-27'
    start_date      date NOT NULL,
    end_date        date NOT NULL,
    is_current      boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, name),
    CHECK (end_date > start_date)
);
-- only one current year per school
CREATE UNIQUE INDEX ux_academic_year_current ON academic_years (school_id) WHERE is_current;

CREATE TABLE classes (                                  -- grade levels, stable across years
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    name            varchar(30) NOT NULL,               -- 'Nursery', 'LKG', '1' .. '12'
    sort_order      smallint NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, name)
);

CREATE TABLE subjects (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    name            varchar(80) NOT NULL,               -- 'Mathematics'
    code            varchar(20),                        -- 'MATH'
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, name)
);

-- ---------------------------------------------------------------------
-- People
-- ---------------------------------------------------------------------
CREATE TABLE teachers (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    user_id         uuid REFERENCES users(id),
    employee_code   varchar(30),
    full_name       varchar(150) NOT NULL,
    phone           varchar(15) NOT NULL,
    email           citext,
    designation     varchar(80),
    deleted_at      timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, phone)
);
CREATE INDEX ix_teachers_school ON teachers (school_id);

CREATE TABLE sections (                                 -- e.g. Class 7 - A in 2026-27
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id           uuid NOT NULL REFERENCES schools(id),
    academic_year_id    uuid NOT NULL REFERENCES academic_years(id),
    class_id            uuid NOT NULL REFERENCES classes(id),
    name                varchar(10) NOT NULL,           -- 'A'
    class_teacher_id    uuid REFERENCES teachers(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (academic_year_id, class_id, name)
);
CREATE INDEX ix_sections_school ON sections (school_id);

CREATE TABLE section_subjects (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    section_id      uuid NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    subject_id      uuid NOT NULL REFERENCES subjects(id),
    UNIQUE (section_id, subject_id)
);

CREATE TABLE teacher_assignments (                      -- who teaches what
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    teacher_id      uuid NOT NULL REFERENCES teachers(id),
    section_id      uuid NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    subject_id      uuid NOT NULL REFERENCES subjects(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (section_id, subject_id, teacher_id)
);
CREATE INDEX ix_teacher_assign_teacher ON teacher_assignments (teacher_id);

CREATE TABLE students (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    user_id         uuid REFERENCES users(id),          -- created when student login is enabled
    admission_no    varchar(30) NOT NULL,
    full_name       varchar(150) NOT NULL,
    date_of_birth   date,
    gender          gender_type,
    pin_hash        text,                               -- Argon2; student login
    failed_logins   smallint NOT NULL DEFAULT 0,
    locked_until    timestamptz,
    deleted_at      timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, admission_no)
);
CREATE INDEX ix_students_school ON students (school_id);

CREATE TABLE student_enrolments (                       -- student in a section for a year
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id           uuid NOT NULL REFERENCES schools(id),
    student_id          uuid NOT NULL REFERENCES students(id),
    academic_year_id    uuid NOT NULL REFERENCES academic_years(id),
    section_id          uuid NOT NULL REFERENCES sections(id),
    roll_no             varchar(10),
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (student_id, academic_year_id)
);
CREATE INDEX ix_enrol_section ON student_enrolments (section_id);

CREATE TABLE guardians (                                -- parents
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    user_id         uuid REFERENCES users(id),
    full_name       varchar(150) NOT NULL,
    phone           varchar(15) NOT NULL,
    email           citext,
    deleted_at      timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, phone)
);
CREATE INDEX ix_guardians_school ON guardians (school_id);

CREATE TABLE student_guardians (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    student_id      uuid NOT NULL REFERENCES students(id),
    guardian_id     uuid NOT NULL REFERENCES guardians(id),
    relation        guardian_relation NOT NULL,
    is_primary      boolean NOT NULL DEFAULT false,
    UNIQUE (student_id, guardian_id)
);
CREATE INDEX ix_student_guardians_guardian ON student_guardians (guardian_id);

-- Role membership (after people tables so FKs resolve)
CREATE TABLE user_roles (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id),
    role            role_type NOT NULL,
    school_id       uuid REFERENCES schools(id),        -- NULL only for PLATFORM_ADMIN
    teacher_id      uuid REFERENCES teachers(id),
    guardian_id     uuid REFERENCES guardians(id),
    student_id      uuid REFERENCES students(id),
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CHECK ( (role = 'PLATFORM_ADMIN' AND school_id IS NULL)
         OR (role <> 'PLATFORM_ADMIN' AND school_id IS NOT NULL) ),
    CHECK ( role <> 'TEACHER' OR teacher_id  IS NOT NULL ),
    CHECK ( role <> 'PARENT'  OR guardian_id IS NOT NULL ),
    CHECK ( role <> 'STUDENT' OR student_id  IS NOT NULL )
);
CREATE UNIQUE INDEX ux_user_roles ON user_roles
    (user_id, role, COALESCE(school_id, '00000000-0000-0000-0000-000000000000'::uuid));

ALTER TABLE refresh_tokens
    ADD CONSTRAINT fk_refresh_user_role FOREIGN KEY (user_role_id) REFERENCES user_roles(id);

-- ---------------------------------------------------------------------
-- Grading
-- ---------------------------------------------------------------------
CREATE TABLE grade_scales (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    name            varchar(60) NOT NULL,               -- 'CBSE 8-point'
    is_default      boolean NOT NULL DEFAULT false,
    UNIQUE (school_id, name)
);
CREATE UNIQUE INDEX ux_grade_scale_default ON grade_scales (school_id) WHERE is_default;

CREATE TABLE grade_bands (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    grade_scale_id  uuid NOT NULL REFERENCES grade_scales(id) ON DELETE CASCADE,
    grade           varchar(5) NOT NULL,                -- 'A1'
    min_percent     numeric(5,2) NOT NULL,              -- inclusive
    max_percent     numeric(5,2) NOT NULL,              -- inclusive
    grade_point     numeric(4,2),
    CHECK (min_percent >= 0 AND max_percent <= 100 AND min_percent <= max_percent)
);

-- ---------------------------------------------------------------------
-- Exams and marks
-- ---------------------------------------------------------------------
CREATE TABLE exams (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id           uuid NOT NULL REFERENCES schools(id),
    academic_year_id    uuid NOT NULL REFERENCES academic_years(id),
    name                varchar(80) NOT NULL,           -- 'Half-Yearly'
    sequence            smallint NOT NULL,              -- order within the year, for progress charts
    grade_scale_id      uuid REFERENCES grade_scales(id),
    start_date          date,
    end_date            date,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (academic_year_id, name)
);
CREATE INDEX ix_exams_school ON exams (school_id);

CREATE TABLE exam_subjects (                            -- max marks can differ by class
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    exam_id         uuid NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    class_id        uuid NOT NULL REFERENCES classes(id),
    subject_id      uuid NOT NULL REFERENCES subjects(id),
    max_marks       numeric(6,2) NOT NULL CHECK (max_marks > 0),
    pass_marks      numeric(6,2),                       -- NULL = school pass_percent of max
    exam_date       date,
    UNIQUE (exam_id, class_id, subject_id),
    CHECK (pass_marks IS NULL OR (pass_marks >= 0 AND pass_marks <= max_marks))
);

CREATE TABLE marks (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id           uuid NOT NULL REFERENCES schools(id),
    exam_subject_id     uuid NOT NULL REFERENCES exam_subjects(id),
    student_id          uuid NOT NULL REFERENCES students(id),
    section_id          uuid NOT NULL REFERENCES sections(id),   -- denormalised for fast section queries
    status              mark_status NOT NULL DEFAULT 'PRESENT',
    marks_obtained      numeric(6,2),
    entered_by          uuid REFERENCES users(id),
    version             integer NOT NULL DEFAULT 1,     -- bump on every change (PDF cache key)
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (exam_subject_id, student_id),
    CHECK ( (status = 'PRESENT' AND marks_obtained IS NOT NULL AND marks_obtained >= 0)
         OR (status <> 'PRESENT' AND marks_obtained IS NULL) )
    -- marks_obtained <= max_marks is validated in the service layer (needs a join)
);
CREATE INDEX ix_marks_section ON marks (section_id, exam_subject_id);
CREATE INDEX ix_marks_student ON marks (student_id);

CREATE TABLE marks_submissions (                        -- teacher workflow per section x exam subject
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id           uuid NOT NULL REFERENCES schools(id),
    exam_subject_id     uuid NOT NULL REFERENCES exam_subjects(id),
    section_id          uuid NOT NULL REFERENCES sections(id),
    status              submission_status NOT NULL DEFAULT 'DRAFT',
    submitted_by        uuid REFERENCES users(id),
    submitted_at        timestamptz,
    UNIQUE (exam_subject_id, section_id)
);

CREATE TABLE result_publications (                      -- controls parent/student visibility
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    exam_id         uuid NOT NULL REFERENCES exams(id),
    section_id      uuid NOT NULL REFERENCES sections(id),
    published_by    uuid NOT NULL REFERENCES users(id),
    published_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (exam_id, section_id)
);

-- ---------------------------------------------------------------------
-- Consent, devices, imports, audit
-- ---------------------------------------------------------------------
CREATE TABLE consent_texts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    version         integer NOT NULL,
    body            text NOT NULL,
    is_current      boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (school_id, version)
);
CREATE UNIQUE INDEX ux_consent_current ON consent_texts (school_id) WHERE is_current;

CREATE TABLE consents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    guardian_id     uuid NOT NULL REFERENCES guardians(id),
    consent_text_id uuid NOT NULL REFERENCES consent_texts(id),
    accepted_at     timestamptz NOT NULL DEFAULT now(),
    withdrawn_at    timestamptz,
    ip_address      inet,
    user_agent      text
);
CREATE INDEX ix_consents_guardian ON consents (guardian_id);

CREATE TABLE devices (                                  -- FCM push tokens
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id),
    fcm_token       text NOT NULL UNIQUE,
    platform        varchar(10) NOT NULL DEFAULT 'android',
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE imports (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id       uuid NOT NULL REFERENCES schools(id),
    type            import_type NOT NULL,
    status          import_status NOT NULL DEFAULT 'UPLOADED',
    file_key        text NOT NULL,                      -- S3 object key
    context         jsonb NOT NULL DEFAULT '{}'::jsonb, -- e.g. {"exam_subject_id":..., "section_id":...}
    total_rows      integer,
    valid_rows      integer,
    errors          jsonb NOT NULL DEFAULT '[]'::jsonb, -- [{"row":14,"column":"phone","message":"..."}]
    created_by      uuid NOT NULL REFERENCES users(id),
    committed_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_imports_school ON imports (school_id, created_at DESC);

CREATE TABLE audit_logs (
    id              bigserial PRIMARY KEY,
    school_id       uuid REFERENCES schools(id),
    user_id         uuid REFERENCES users(id),
    role            role_type,
    action          varchar(60) NOT NULL,               -- 'MARK_UPDATE','RESULT_PUBLISH','LOGIN', ...
    entity          varchar(60),
    entity_id       uuid,
    old_value       jsonb,
    new_value       jsonb,
    reason          text,
    ip_address      inet,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_school_time ON audit_logs (school_id, created_at DESC);
CREATE INDEX ix_audit_entity ON audit_logs (entity, entity_id);

-- ---------------------------------------------------------------------
-- Reporting view: one row per student per exam (marks rules from DESIGN.md §8)
--   ABSENT -> 0 obtained, max counted; EXEMPT -> excluded from both.
--   security_invoker: the view is evaluated with the CALLER's privileges, so
--   the RLS policies on marks/exam_subjects still apply (a plain view runs as
--   its owner, which bypasses RLS and would leak other schools' rows).
-- ---------------------------------------------------------------------
CREATE VIEW v_student_exam_results WITH (security_invoker = true) AS
WITH per_subject AS (
    SELECT
        m.school_id,
        es.exam_id,
        m.section_id,
        m.student_id,
        es.subject_id,
        es.max_marks,
        m.status,
        m.marks_obtained,
        COALESCE(es.pass_marks, es.max_marks * s.pass_percent / 100) AS pass_marks
    FROM marks m
    JOIN exam_subjects es ON es.id = m.exam_subject_id
    JOIN schools s        ON s.id  = m.school_id
),
agg AS (
    SELECT
        school_id, exam_id, section_id, student_id,
        SUM(CASE WHEN status = 'PRESENT' THEN marks_obtained ELSE 0 END)      AS total_obtained,
        SUM(CASE WHEN status <> 'EXEMPT' THEN max_marks ELSE 0 END)           AS total_max,
        COUNT(*) FILTER (WHERE status <> 'EXEMPT'
                           AND COALESCE(marks_obtained, 0) < pass_marks)       AS subjects_failed
    FROM per_subject
    GROUP BY school_id, exam_id, section_id, student_id
)
SELECT
    a.*,
    ROUND(100.0 * a.total_obtained / NULLIF(a.total_max, 0), 2)              AS percentage,
    (a.subjects_failed = 0)                                                   AS passed,
    DENSE_RANK() OVER (PARTITION BY a.exam_id, a.section_id
                       ORDER BY a.total_obtained / NULLIF(a.total_max, 0) DESC NULLS LAST) AS section_rank
FROM agg a;

-- ---------------------------------------------------------------------
-- Row-Level Security (defense in depth; see DESIGN.md §5)
-- The API runs each request in a transaction and executes:
--     SET LOCAL app.school_id = '<uuid from JWT>';
-- Platform-admin/support jobs use a separate DB role with BYPASSRLS.
-- Apply the same policy to every table that has school_id.
-- ---------------------------------------------------------------------
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'academic_years','classes','subjects','teachers','sections','section_subjects',
        'teacher_assignments','students','student_enrolments','guardians','student_guardians',
        'grade_scales','exams','exam_subjects','marks','marks_submissions','result_publications',
        'consent_texts','consents','imports'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I
                 USING (school_id = current_setting(''app.school_id'', true)::uuid)
                 WITH CHECK (school_id = current_setting(''app.school_id'', true)::uuid)', t);
    END LOOP;
END $$;
-- NOTE: RLS does not apply to the table owner. Run the API as a separate,
-- non-owner role (e.g. app_user) so these policies are enforced.
--
-- The Alembic migration additionally grants DML on all tables to the API
-- role (app_user) and never grants it ownership, BYPASSRLS or DDL rights.

"""

TABLES = [
    "schools",
    "users",
    "otp_codes",
    "refresh_tokens",
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
    "user_roles",
    "grade_scales",
    "grade_bands",
    "exams",
    "exam_subjects",
    "marks",
    "marks_submissions",
    "result_publications",
    "consent_texts",
    "consents",
    "devices",
    "imports",
    "audit_logs",
]


def upgrade() -> None:
    bind = op.get_bind()
    # Raw driver call: the DDL contains format() %I placeholders that must not be
    # treated as bind parameters.
    bind.connection.driver_connection.execute(SCHEMA_SQL)  # type: ignore[union-attr]
    role = get_settings().app_db_role
    if not role.isidentifier():
        raise ValueError("APP_DB_ROLE must be a plain identifier")
    # The API role is created by infra (with a password). Create a NOLOGIN placeholder
    # if it is missing so grants never fail on a fresh database.
    bind.exec_driver_sql(
        f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') "  # noqa: S608
        f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$;"
    )
    bind.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {role}")
    bind.exec_driver_sql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}")
    bind.exec_driver_sql(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}")
    # Audit rows are append-only for the API.
    bind.exec_driver_sql(f"REVOKE UPDATE, DELETE ON audit_logs FROM {role}")
    # Marks are never hard-deleted.
    bind.exec_driver_sql(f"REVOKE DELETE ON marks FROM {role}")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP VIEW IF EXISTS v_student_exam_results")
    for t in reversed(TABLES):
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {t} CASCADE")
    for e in [
        "import_status",
        "import_type",
        "submission_status",
        "mark_status",
        "guardian_relation",
        "gender_type",
        "role_type",
    ]:
        bind.exec_driver_sql(f"DROP TYPE IF EXISTS {e}")
