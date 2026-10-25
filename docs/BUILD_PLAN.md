# Build Plan: School Progress App

How to build v1 step by step with a coding agent (Devin / Claude Code).

> **Status (25 Oct 2026):** milestones 0–5 are done. Milestone 6 is done except 6.3 (FCM on the phone needs the Firebase project files; the server side is built) and 6.5 (signing + Play listing). Milestone 7 (deployment, pilot onboarding) is not started. Details and deviations: `DESIGN.md` §14.

**Rule:** give the agent **one task at a time**. Each task ends with tests passing and a pull request you review before merging.
Time estimates assume evenings and weekends (~12–15 hrs/week).

---

## Milestone 0: Project setup (week 1)

| # | Task for the agent | Done when |
|---|---|---|
| 0.1 | Create the monorepo structure from `DESIGN.md §3`, with a `.gitignore` and `infra/docker-compose.yml` (Postgres 16, Redis) | `docker compose up` starts both |
| 0.2 | Backend skeleton: FastAPI app, settings via env, `/health` endpoint, SQLAlchemy + Alembic, pytest, ruff, mypy | `pytest` passes, `/docs` opens |
| 0.3 | Translate `db/schema.sql` into SQLAlchemy models + the first Alembic migration (including RLS policies and the view) | `alembic upgrade head` creates all tables on an empty DB |
| 0.4 | Seed script: 1 demo school, 1 year, classes 6–8 with sections A/B, 6 subjects, 10 teachers, 120 students, parents, 2 exams with random marks | `python -m app.seed` fills the DB |
| 0.5 | GitHub Actions CI for backend (lint, type check, tests against a Postgres service) | CI green on PR |

## Milestone 1: Auth and tenancy (weeks 2–3)

| # | Task | Done when |
|---|---|---|
| 1.1 | OTP request/verify with dev-mode console OTP, rate limits, hashed codes | tests cover expiry, wrong code, rate limit |
| 1.2 | Role selection → JWT access + rotating refresh tokens; `/me`; logout | tests cover refresh rotation and revoked tokens |
| 1.3 | Student login (school code + admission no + PIN), lockout after 5 failures | tests pass |
| 1.4 | **Tenant guard dependency**: sets `app.school_id` per request transaction; app connects as non-owner DB role | test: school B token cannot read school A data |
| 1.5 | Permission helpers: `require_role(...)`, `teacher_can_access(section, subject)`, `guardian_can_access(student)` | unit tests per role |
| 1.6 | Audit log helper; log logins | rows appear in `audit_logs` |

## Milestone 2: School setup and imports (weeks 4–5)

| # | Task | Done when |
|---|---|---|
| 2.1 | CRUD APIs: academic years, classes, sections, subjects, section subjects | tests + OpenAPI docs |
| 2.2 | CRUD APIs: teachers, teacher assignments, students, enrolments, guardians, links | tests incl. soft delete |
| 2.3 | Import framework: template download, upload to S3 (MinIO locally), background validation, preview, commit in one transaction | sample file with errors shows correct row messages |
| 2.4 | Student + parent import and teacher import, upserting by natural keys; creates `users` + `user_roles` | 500-row file imports in < 30 s |
| 2.5 | Platform admin: create school + school admin | works end to end |

## Milestone 3: Exams, marks, results (weeks 6–7)

| # | Task | Done when |
|---|---|---|
| 3.1 | Exams + exam subjects APIs; default CBSE grade scale created for new schools | tests |
| 3.2 | Marks grid API (get / bulk put) with validation (≤ max, AB/EX) and teacher permission checks; audit every change | IDOR + permission tests |
| 3.3 | Marks Excel template (pre-filled names) + import | round-trip test |
| 3.4 | Submit marks; exam status endpoint (submitted / pending per section × subject) | tests |
| 3.5 | Publish / unpublish per section; students and parents only see published results | test: unpublished marks invisible to parent |
| 3.6 | Results APIs: results list, exam detail, progress series (grade, %, rank from the view) | numbers match hand-calculated fixtures |
| 3.7 | Report card PDF (WeasyPrint), cached by marks version | PDF renders with logo, totals, grade |

## Milestone 4: Dashboards (week 8)

| # | Task | Done when |
|---|---|---|
| 4.1 | Dashboard APIs: summary, sections, subjects, attention list, toppers | tests vs seed data; < 500 ms on 1,500 students |
| 4.2 | Excel export for each dashboard table | file opens in Excel |

## Milestone 5: Web app (weeks 9–11)

| # | Task | Done when |
|---|---|---|
| 5.1 | Next.js + TypeScript + Tailwind + shadcn/ui setup, API client generated from OpenAPI, auth (OTP + student) | login works against local API |
| 5.2 | Public landing page + school page + privacy/terms pages | Lighthouse ≥ 90 on mobile |
| 5.3 | Admin screens: setup pages + import wizard (upload → preview → commit) | full onboarding of a demo school via UI |
| 5.4 | Teacher screens: my classes, marks grid (keyboard friendly), upload | marks for one section entered in < 5 min |
| 5.5 | Principal screens: dashboard with charts, exam status, publish, drill-down, student profile | |
| 5.6 | Parent/student screens: results, exam detail, progress chart, report card download, consent screen | |

## Milestone 6: Android app (weeks 12–14)

| # | Task | Done when |
|---|---|---|
| 6.1 | Flutter project, theming, API client, secure token storage, login flows | runs on a real Android phone |
| 6.2 | Parent/student: children list, home with latest result + chart, exams, report card | |
| 6.3 | Push notifications (FCM) on publish; device registration API | notification arrives on publish |
| 6.4 | Principal summary + teacher marks entry (simple) | |
| 6.5 | Release build, app icon, Play Store listing (internal testing track first) | installable from Play internal testing |

## Milestone 7: Pilot readiness (week 15)

- Deploy staging + production in India region; backups; Sentry; uptime alert
- Security pass: run the IDOR/tenant tests, check rate limits, remove dev OTP in prod
- Write a one-page onboarding guide + Excel templates for schools
- Onboard pilot school #1 with real data (after the data processing agreement is signed)

---

## v2 backlog (after pilot; order by what schools ask for)

1. Attendance (daily, per section) + absence alert to parents
2. Notices / circulars / homework
3. Fee reminders + UPI payment links
4. WhatsApp notifications (results, absences)
5. Telugu / Hindi interface
6. School-branded app (white-label), premium tier
7. AI: auto-generated report card remarks, weak-topic insights for teachers
8. Multi-branch dashboards for school chains
9. iOS app

---

## How to prompt the coding agent (template)

```
Read AGENTS.md, docs/MVP_SPEC.md and docs/DESIGN.md first.

Task 3.2: Marks grid API.
- Endpoints: GET /api/v1/marks?exam_subject_id=&section_id=  and  PUT /api/v1/marks/bulk
- Follow DESIGN.md §5 (permissions), §7 (API), §8 (validation rules).
- Teachers may only access sections + subjects in teacher_assignments, and only while not published.
- Write every change to audit_logs with old and new values.
- Tests required: happy path; marks > max rejected; AB/EX handled; teacher of another
  section gets 403; parent token gets 403; school B token gets 404.
- Do not change other modules. Open a PR with a short summary.
```
