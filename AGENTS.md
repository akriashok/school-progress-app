# Instructions for coding agents (Devin, Claude Code, others)

You are building a **multi-school SaaS** where teachers upload marks and principals, students and parents view results and progress. It holds **children's personal data**, so correctness of access control matters more than speed.

## Read first
1. `docs/MVP_SPEC.md`: what to build (and what NOT to build)
2. `docs/DESIGN.md`: architecture, API, permissions, business rules
3. `db/schema.sql`: reference data model
4. `docs/BUILD_PLAN.md`: task list; work on one task at a time

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 16, Redis + ARQ/Celery, pytest
- Web: Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, Recharts
- Mobile: Flutter 3, Riverpod, Dio, fl_chart
- Local dev: `infra/docker-compose.yml`

## Non-negotiable rules
1. **Tenant isolation:** every query on a school-owned table is scoped by `school_id` from the JWT. Never accept `school_id` from the request body or query string. Use the shared tenant-guard dependency; never bypass it.
2. **Row-level permissions:** teachers only touch their assigned section + subject; parents only their linked children; students only themselves. Parents and students only ever see **published** results.
3. **Every new read endpoint needs tests** proving: another school's user gets 404, and a parent/student cannot access another child by changing an id (IDOR).
4. **Audit:** log every marks change, publish/unpublish, import commit, export and platform-admin access to `audit_logs`.
5. **No personal data in logs** (no phone numbers, names or marks). Use ids.
6. **No secrets in git.** Config comes from environment variables. Dev-mode OTP must be impossible to enable in production.
7. **Out-of-scope features** (fees, attendance, chat, etc.) must not be built unless the task explicitly asks for it.
8. **Schema changes** go through Alembic migrations; update `db/schema.sql` and `DESIGN.md` in the same PR if the model changes.
9. **Don't add third-party analytics, ads or tracking SDKs** to web or mobile.

## Conventions
- API under `/api/v1`, REST, JSON, UUID ids, paginated lists, error shape `{ "error": { "code", "message", "details" } }`
- Backend layout: routers in `app/api/v1`, business logic in `app/services`, no SQL in routers
- Python: ruff + mypy strict on new code; type hints everywhere
- TypeScript: strict mode; API client generated from the OpenAPI spec
- UI text through i18n keys (English only in v1, Telugu/Hindi later)
- Commits: small and focused; PR description lists what changed and how it was tested

## Definition of done for a task
- [ ] Code + tests written; all tests and linters pass locally and in CI
- [ ] Permission and tenant tests included for any new endpoint
- [ ] OpenAPI docs accurate
- [ ] No out-of-scope changes
- [ ] PR opened with a short summary
