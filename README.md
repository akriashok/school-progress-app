# School Progress App (working name: VidyaTrack)

A multi-school SaaS for Indian schools: teachers upload marks once, and **principals, students and parents** see results, report cards and progress on the **web** and an **Android app**.

## Status

v1 is built: milestones 0–5 in full, milestone 6 except push registration on the phone. See "What is left" below.

| Part | Folder | Checks |
|---|---|---|
| API (FastAPI, PostgreSQL with RLS) | `backend/` | 111 pytest tests (tenant isolation, IDOR, permissions, business rules, imports, PDFs) · ruff · mypy strict |
| Web (Next.js 15) | `web/` | eslint · tsc strict · production build · browser walk-through of every role |
| Android (Flutter 3) | `mobile/` | flutter analyze · flutter test |
| Local infra | `infra/` | Postgres 16 + Redis via Docker Compose |
| CI | `.github/workflows/ci.yml` | backend, web and mobile jobs |

## Documents

| File | What it is |
|---|---|
| [docs/MVP_SPEC.md](docs/MVP_SPEC.md) | What v1 does and does not do |
| [docs/DESIGN.md](docs/DESIGN.md) | Architecture, permissions, API, business rules; §14 records what was built and every deviation |
| [db/schema.sql](db/schema.sql) | Reference schema (kept in sync with the Alembic migrations) |
| [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) | Milestones and the v2 backlog |
| [AGENTS.md](AGENTS.md) | Rules for coding agents |

## Run it in GitHub Codespaces (demo link)

1. On the repository page click **Code → Codespaces → Create codespace on main**.
2. Wait 5–8 minutes the first time. Setup installs everything, creates the database, loads the demo school and starts the app.
3. Open the **Ports** tab. Port **3000** is the web app. To share it, right-click it, choose **Port visibility → Public**, and copy the `https://…-3000.app.github.dev` link.

Logs are in `.devcontainer/logs/`. The codespace sleeps after about 30 minutes of inactivity; reopening it restarts the app on the same link. **Demo data only:** Codespaces run outside India.

## Run it locally

Prerequisites: Docker Desktop, [uv](https://docs.astral.sh/uv/), Node 22+. Flutter is optional (it can also run in Docker, see below).

```bash
# 1. Database + Redis (ports 5433 and 6380, so they don't clash with local installs)
cd infra && docker compose up -d

# 2. API on http://localhost:8000  (docs at /docs)
cd backend
cp .env.example .env              # dev settings; set JWT_SECRET to a random string
uv sync --python 3.12
uv run alembic upgrade head
uv run python -m app.seed         # demo school; prints the logins below
uv run uvicorn app.main:app --reload

# 3. Web on http://localhost:3000
cd web
npm install
npm run dev
```

**Demo logins** (local only; dev OTP is always `123456`):

| Role | Login |
|---|---|
| Platform admin | phone `9000000000` |
| School admin | phone `9000000001` |
| Principal | phone `9000000002` |
| Teacher | phone `9100000001` |
| Parent (two children) | phone `9200000001` |
| Student | school `DEMO01`, admission `A1001`, PIN `1234` |

**School website:** http://localhost:3000/schools/DEMO01 shows the demo school's public site. The school admin edits it under **School website** in the app. To make it the home page, start the web app with `HOME_SCHOOL_CODE=DEMO01`.

The seed creates one school (DEMO01), classes 6–8 with sections A/B, 6 subjects, 10 teachers, 120 students with parents, and two exams with marks. Unit Test 1 is published for all sections; Half-Yearly only for the A sections.

### Tests

```bash
cd backend && uv run pytest          # uses the vidyatrack_test database from infra/postgres/init.sql
cd web && npm run lint && npm run typecheck && npm run build
cd mobile && flutter analyze && flutter test
```

Report-card PDFs use WeasyPrint, which needs Pango. That library isn't available on plain Windows, so there the PDF test is skipped and the endpoint returns 503. To run the full suite including PDFs, use the API image:

```bash
cd backend && docker build -t vidyatrack-api .
docker run --rm --network vidyatrack_default \
  -e TEST_DATABASE_URL=postgresql+psycopg://app_user:app_user_dev@postgres:5432/vidyatrack_test \
  -e TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://vidya_owner:vidya_owner_dev@postgres:5432/vidyatrack_test \
  vidyatrack-api python -m pytest -q
```

### Android app

```bash
cd mobile
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000     # emulator -> API on your PC
flutter build apk --release --dart-define=API_BASE_URL=https://api.your-domain.in
```

Debug builds allow plain HTTP to the local API; release builds are HTTPS-only.

### Changing the API

After changing an endpoint, regenerate the web client: `uv run python -m app.export_openapi ../web/openapi.json` in `backend/`, then `npm run gen:api` in `web/`. CI fails if either file is stale.

## Security model (summary)

- Every school-owned table has Postgres Row-Level Security. The API connects as `app_user` (not owner, no BYPASSRLS), and each request's transaction is scoped to the school in the JWT. `school_id` is never read from the request.
- Teachers can only reach their own section + subject; parents only their linked children; students only themselves; parents and students only see **published** results. A tenant/IDOR test covers every read endpoint.
- Every mark change, publish/unpublish, import commit, export, PIN reset and platform-admin access is written to `audit_logs`. Logs contain ids only, never names, phones or marks.
- Production config refuses to start with dev OTP, a weak JWT secret, console SMS or insecure cookies.

## What is left before the pilot

1. **Push on the phone (BUILD_PLAN 6.3):** create the Firebase project, add `google-services.json` and `firebase_messaging` to the app, and call `POST /api/v1/devices`. The server side (device registration and FCM send on publish) is done.
2. **SMS provider:** set `SMS_BACKEND=http`, `SMS_HTTP_URL` and `SMS_HTTP_API_KEY` for a DLT-registered OTP template.
3. **Release signing + Play Store listing (6.5)** and an app icon. A release APK already builds (`flutter build apk --release`).
4. **Deploy (milestone 7):** Mumbai region, managed Postgres with `app_user` created by infra, S3 bucket (`STORAGE_BACKEND=s3`), Sentry, backups, uptime alert.
5. **Legal review** of the privacy policy, terms and default consent text (drafts are in the app).
6. Decide the open questions in MVP_SPEC §11 (rank default, co-scholastic grades, primary-class grading, SMS cost, report-card layout).
