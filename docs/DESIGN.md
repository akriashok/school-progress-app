# Technical Design: School Progress App

**Version:** 1.0 (draft) · **Date:** 25 Oct 2026 · Read with `MVP_SPEC.md` and `../db/schema.sql`.

---

## 1. Architecture overview

```
 Users:  Principal / School admin / Teacher        Student / Parent
               │  (mostly web)                        │  (mostly Android)
               ▼                                      ▼
        ┌──────────────┐                      ┌──────────────┐
        │  Web app     │                      │ Android app  │
        │  Next.js     │                      │ Flutter      │
        └──────┬───────┘                      └──────┬───────┘
               │        HTTPS + JSON (REST, JWT)     │
               └──────────────────┬──────────────────┘
                                  ▼
                   ┌─────────────────────────────┐
                   │  Backend API (FastAPI)      │
                   │  auth · RBAC · tenant guard │
                   │  imports · reports · PDFs   │
                   └───┬──────────┬──────────┬───┘
                       ▼          ▼          ▼
                 PostgreSQL   Object store   External
                 (all data)   (S3: logos,    services:
                              imports, PDFs) SMS OTP, FCM push
```

- **One backend, one database, many schools (multi-tenant SaaS).** Every school-owned row carries `school_id`.
- Web and Android are both thin clients over the same REST API. No business logic in the clients.
- Everything hosted in **India** (AWS `ap-south-1` Mumbai, or an India region of a managed provider).

## 2. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12, **FastAPI**, Pydantic v2 | Async; auto OpenAPI docs at `/docs` |
| ORM / migrations | SQLAlchemy 2.0 + **Alembic** | `db/schema.sql` is the reference; Alembic migrations are the source of truth once code exists |
| Database | **PostgreSQL 16** | Managed: AWS RDS, Supabase or Neon (India region) |
| Background jobs | ARQ or Celery + Redis | Excel import processing, PDF generation, push notifications |
| Web | **Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui** | Charts: Recharts. Tables: TanStack Table |
| Mobile | **Flutter 3** (Dart), Riverpod, Dio, fl_chart | Android first; iOS later from the same code |
| Excel | `openpyxl` / `pandas` on backend | Templates generated per school/section |
| PDF | WeasyPrint (HTML → PDF) | Report cards from an HTML template |
| Auth | Phone OTP (SMS provider with DLT-registered template) + JWT | Student: school code + admission no + PIN |
| Push | Firebase Cloud Messaging | |
| Files | S3 (Mumbai) with presigned URLs | Private bucket; no public files except logos |
| Hosting | Docker → AWS ECS Fargate or a single EC2/Lightsail at pilot stage | Web on Vercel (or same AWS) |
| CI/CD | GitHub Actions | Lint, tests, build, deploy |
| Monitoring | Sentry (errors), CloudWatch / Grafana (metrics), uptime check | |

**Cheapest pilot setup:** one small VM in Mumbai running Docker Compose (API + worker + Redis), a managed Postgres, S3, and Next.js on Vercel. Move to ECS when you have 20+ schools.

## 3. Repository structure (monorepo)

```
school_aplication/
├── AGENTS.md / CLAUDE.md      # instructions for coding agents
├── README.md
├── docs/                      # MVP_SPEC, DESIGN, BUILD_PLAN
├── db/schema.sql              # reference schema
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # config, security, deps (current_user, tenant guard)
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── api/v1/            # routers: auth, schools, academics, people, exams, marks, reports, imports
│   │   ├── services/          # business logic (grading, ranking, imports, pdf, notifications)
│   │   └── workers/           # background jobs
│   ├── alembic/
│   ├── tests/                 # pytest; includes tenant-isolation tests
│   └── pyproject.toml
├── web/                       # Next.js app
├── mobile/                    # Flutter app
├── infra/                     # docker-compose.yml, Dockerfiles, terraform (later)
└── .github/workflows/
```

## 4. Data model

Full DDL: `db/schema.sql`. Main entities:

```
schools ─┬─ academic_years ─┬─ exams ── exam_subjects ── marks ── students
         │                  └─ sections ─┬─ section_subjects ── subjects
         │                               └─ teacher_assignments ── teachers
         ├─ classes (grade levels: Nursery..12) ── sections
         ├─ grade_scales ── grade_bands
         ├─ students ── student_guardians ── guardians (parents)
         ├─ result_publications (exam × section)
         └─ audit_logs

users (one per real person, identified by phone) ── user_roles (role + school + linked teacher/guardian/student)
```

Key design decisions:

1. **`users` is global; `user_roles` is per school.** One phone number = one user. A teacher who is also a parent gets two `user_roles` rows. A parent with children in two schools gets two rows.
2. **Enrolment per academic year.** `student_enrolments` maps student → section → academic year, so history is kept when a student moves to the next class.
3. **Marks are stored once per (student, exam_subject).** `marks_obtained` is numeric and nullable; `status` holds `PRESENT | ABSENT | EXEMPT`.
4. **Visibility is controlled by `result_publications`** (exam × section). Students and parents can only read marks where a publication row exists.
5. **Grades and ranks are computed, not stored**, using SQL views or service functions, so they're always consistent with marks. Cache later if needed.
6. **Soft delete** (`deleted_at`) for people; never hard-delete marks (audit).

## 5. Multi-tenancy and access control (most important part)

Every request goes through three checks:

1. **Authenticate:** a valid JWT gives you `user_id`, the active `role`, `school_id`, and the linked entity id (`teacher_id` / `guardian_id` / `student_id`).
2. **Tenant guard:** every query on school-owned tables **must** filter by `school_id = token.school_id`. Implement this in a single repository/dependency layer, not hand-written in each endpoint.
3. **Row-level permission:**

| Role | Students | Marks read | Marks write |
|---|---|---|---|
| platform_admin | all (support only, audited) | all | no |
| school_admin | own school | own school (draft + published) | own school |
| principal | own school | own school (draft + published) | can publish/unpublish; edit allowed, audited |
| teacher | sections they teach | sections + subjects they teach | only own section+subject, only while not published (or with principal unlock) |
| parent | only linked children | only linked children, **published only** | no |
| student | only self | only self, **published only** | no |

**Defense in depth:** also enable PostgreSQL Row-Level Security on school-owned tables using `current_setting('app.school_id')`, set per request transaction. Even if an endpoint forgets a filter, Postgres blocks cross-school reads.

**Mandatory tests:** for every read endpoint, a test that school B's user gets 404/403 for school A's ids, and a parent cannot read another child's marks by changing the id in the URL (IDOR).

## 6. Authentication

**OTP flow (staff and parents)**
1. `POST /auth/otp/request {phone}` → if the phone exists in `users`, send a 6-digit OTP (valid 5 min). Always return 200 (don't reveal whether the number exists).
2. `POST /auth/otp/verify {phone, otp}` → returns the list of available roles/schools.
3. `POST /auth/session {role_id}` → returns `access_token` (15 min) + `refresh_token` (30 days, rotating, stored hashed in `refresh_tokens`).
4. `POST /auth/refresh`, `POST /auth/logout`.

**Student flow:** `POST /auth/student/login {school_code, admission_no, pin}` → tokens. PIN hashed with Argon2. Lock for 15 min after 5 failed attempts.

**Rate limits:** OTP request 3 per phone per 10 min and 20 per IP per hour; verify 5 attempts per OTP.

**Dev mode:** in local/dev, the OTP is logged to the console and a fixed test OTP is allowed. This must be impossible in production; the config check refuses to start.

## 7. API design (REST, `/api/v1`)

Conventions: JSON; ids are UUIDs; `school_id` comes **from the token, never from the request body**; lists are paginated (`?page=&page_size=`); errors are `{ "error": { "code", "message", "details" } }`.

### Auth
| Method | Path | Who |
|---|---|---|
| POST | `/auth/otp/request` · `/auth/otp/verify` · `/auth/session` · `/auth/refresh` · `/auth/logout` | public / any |
| POST | `/auth/student/login` | public |
| GET | `/me` | any |

### School setup (school_admin; principal read)
| Method | Path |
|---|---|
| GET/PATCH | `/school` (profile, logo) |
| CRUD | `/academic-years`, `/classes`, `/sections`, `/subjects`, `/sections/{id}/subjects` |
| CRUD | `/teachers`, `/teacher-assignments` |
| CRUD | `/students`, `/students/{id}/guardians`, `/guardians` |
| CRUD | `/grade-scales` |

### Imports (school_admin, teacher for marks)
| Method | Path | Notes |
|---|---|---|
| GET | `/imports/templates/{type}` | `students`, `teachers`, `marks?exam_subject_id=&section_id=` → .xlsx |
| POST | `/imports/{type}` | upload → returns `import_id`, runs validation in background |
| GET | `/imports/{import_id}` | status + row-level errors + preview |
| POST | `/imports/{import_id}/commit` | apply valid rows in one transaction |

### Exams and marks
| Method | Path | Who |
|---|---|---|
| CRUD | `/exams`, `/exams/{id}/subjects` (max marks, pass marks, date) | school_admin |
| GET | `/teacher/my-assignments` | teacher |
| GET | `/marks?exam_subject_id=&section_id=` | teacher (own), principal, admin |
| PUT | `/marks/bulk` `{exam_subject_id, section_id, entries:[{student_id, marks, status}]}` | teacher (own), admin |
| POST | `/marks/submit` `{exam_subject_id, section_id}` | teacher |
| GET | `/exams/{id}/status` (submitted/pending per section × subject) | principal, admin |
| POST/DELETE | `/exams/{id}/publications` `{section_ids}` | principal, admin |

### Results (parent/student; principal/admin for any student)
| Method | Path |
|---|---|
| GET | `/children` (parent) |
| GET | `/students/{id}/results` (exam list with totals, %, grade, rank) |
| GET | `/students/{id}/results/{exam_id}` (subject-wise) |
| GET | `/students/{id}/progress` (series for charts) |
| GET | `/students/{id}/report-cards/{exam_id}.pdf` |

### Dashboards (principal, admin)
| Method | Path |
|---|---|
| GET | `/dashboard/summary?exam_id=` |
| GET | `/dashboard/sections?exam_id=` |
| GET | `/dashboard/subjects?exam_id=&class_id=` |
| GET | `/dashboard/attention?exam_id=` |
| GET | `/dashboard/toppers?exam_id=&section_id=` |
| GET | `/dashboard/export?report=&exam_id=` → .xlsx |

### Consent and notifications
| Method | Path |
|---|---|
| GET | `/consent/current` · POST `/consent/accept` |
| POST | `/devices` (register FCM token) · DELETE `/devices/{id}` |

### Platform admin
| Method | Path |
|---|---|
| CRUD | `/admin/schools`, POST `/admin/schools/{id}/admins` |

## 8. Business rules

- **Percentage** = Σ marks_obtained ÷ Σ max_marks of subjects where status = PRESENT, × 100. ABSENT counts as 0 with max included; EXEMPT is excluded from both.
- **Pass** in a subject: marks ≥ `pass_marks` (default 33% of max). Overall pass: passed every non-exempt subject.
- **Grade:** look up the percentage in the school's `grade_bands` (default CBSE: A1 91–100, A2 81–90, B1 71–80, B2 61–70, C1 51–60, C2 41–50, D 33–40, E < 33).
- **Rank:** dense rank by percentage within section for the exam; ties share a rank; hidden if `schools.show_rank = false`.
- **Needs attention:** fails in ≥ 2 subjects **or** percentage dropped ≥ 10 points vs the previous exam in the same academic year.
- **Marks validation:** 0 ≤ marks ≤ max_marks; up to 2 decimals; `AB`/`EX` strings accepted in Excel.
- **Editing after publish:** teachers can't edit. Principal/admin can, with a required reason; it's logged, and parents get no new notification by default.

## 9. Excel import design

1. User downloads a template: headers fixed, plus a hidden sheet with ids for marks templates.
2. Upload → stored in S3 → `imports` row status `VALIDATING` → background job parses each row.
3. Row errors are stored as JSON (`row`, `column`, `message`), e.g. "Row 14: phone must be 10 digits", "Row 22: marks 105 > max 100".
4. UI shows a preview: N valid, M errors, and a downloadable error file.
5. Commit applies valid rows in **one transaction**, upserting by natural key (admission_no; teacher phone; student+exam_subject).
6. Max 5,000 rows per file.

## 10. Report card PDF

- HTML template (Jinja2) → WeasyPrint → PDF, generated on request and cached in S3 by `(student, exam, marks_version)`.
- Content: school logo/name/address, student details, subject-wise marks, total, %, grade, rank (optional), class teacher remark (v2), signature lines.
- One generic template in v1; per-board layouts later.

## 11. Security and DPDP checklist (build-time)

- [ ] HTTPS everywhere; HSTS; secure cookies for web refresh token (httpOnly, SameSite=Lax)
- [ ] Tenant guard + Postgres RLS + IDOR tests
- [ ] Argon2 for PINs; OTPs hashed; secrets in AWS Secrets Manager / env, never in git
- [ ] Rate limits on auth endpoints
- [ ] Audit log: logins, marks create/update, publish/unpublish, imports, exports, platform-admin access
- [ ] Input validation via Pydantic; parameterised SQL only
- [ ] Uploaded files: size limit, type check, private S3, virus scan later
- [ ] No analytics SDKs or ads in the apps; crash reporting without personal data
- [ ] Parent consent record (`consents` table) with version + timestamp
- [ ] School data export (all of a school's data as Excel) and deletion on contract end
- [ ] Backups encrypted, restore tested
- [ ] Data Processing Agreement signed with each school (legal, not code)

## 12. Environments and deployment

| Env | Purpose | Data |
|---|---|---|
| local | Docker Compose (Postgres, Redis, API, worker), dev OTP | seed script with 1 demo school |
| staging | auto-deploy from `main` | demo data only, never real students |
| production | deploy on tagged release | real data, India region |

CI (GitHub Actions): `ruff` + `mypy` + `pytest` (backend) · `eslint` + `tsc` + build (web) · `flutter analyze` + `flutter test` (mobile).

## 13. Observability

- Sentry for backend, web and Flutter (scrub phone numbers and names).
- Structured JSON logs with `request_id`, `school_id`, `user_id` (no marks or phone numbers in logs).
- Metrics: request latency, error rate, OTP send failures, import job duration.
- Alert on: 5xx rate > 2%, OTP failures, DB CPU > 80%, backup failure.

## 14. As built (v1 implementation notes)

Decisions taken while implementing v1, and where the code differs from the plan above.

**Data model changes** (Alembic migrations; `db/schema.sql` updated to match)
- `0001_initial`: `v_student_exam_results` is created `WITH (security_invoker = true)`. A plain view runs as its owner, which bypasses RLS, so without this the view leaked other schools' rows.
- `0001_initial`: grants DML to the API role (`app_user`) only; `audit_logs` is append-only for it (no UPDATE/DELETE) and `marks` cannot be deleted.
- `0002_demo_requests`: new `demo_requests` table for the landing page "Book a demo" form. The API role may only INSERT into it.
- `0004_school_website`: `schools.website` (jsonb) holds each school's public website content: hero, about, feature cards, facilities, stats, gallery, leadership, admissions banner, contact/social links and theme colours.
- `0003_rls_nullif`: RLS policies use `NULLIF(current_setting('app.school_id', true), '')::uuid`, so a request without a tenant sees no rows instead of raising a cast error.

**Tenant guard.** `app/core/deps.py::tenant_ctx` opens one transaction per request and stores the token's `school_id` on the session. A SQLAlchemy `after_begin` hook runs `set_config('app.school_id', …, true)` for every transaction, so RLS still applies after a mid-request commit. Services also filter by `school_id` explicitly (layer 1). The API connects as `app_user`, which is neither owner nor `BYPASSRLS`; a test asserts this.

**Implementation choices**
- SQLAlchemy is used synchronously (FastAPI runs sync endpoints in a thread pool). This is simpler to test and fast enough for the pilot.
- Background work (import validation, push on publish) uses FastAPI `BackgroundTasks`, with job functions that take ids and open their own tenant-scoped session (`imports.validate_in_background`, `notifications.notify_results_published`). Moving them to ARQ/Redis later is a drop-in change.
- File storage: `STORAGE_BACKEND=local` in dev (MinIO images are no longer published on Docker Hub) and `s3` in staging/production.
- Rate limits use Redis when `REDIS_URL` is set, and in-memory otherwise (tests).
- Parents must accept the current consent text before any child-data endpoint responds (`403 CONSENT_REQUIRED`). This is enforced on the server, not just in the UI.
- Ranks are always visible to staff; `schools.show_rank` controls only the parent and student views.
- Grade bands use contiguous ranges (A2 = 81–90.99, …) so percentages such as 90.5 always get a grade.

**Endpoints added beyond §7**
| Method | Path | Why |
|---|---|---|
| POST | `/auth/switch` | Switch to another of your roles without a new OTP |
| GET | `/public/schools/{code}`, `/public/schools/{code}/logo`; POST `/public/demo-requests` | Public school page and landing form |
| GET/POST/DELETE | `/staff` | School admin manages principal/admin logins |
| GET | `/audit-logs` | Recent activity for managers |
| POST | `/students/{id}/pin` | Set or reset the student login PIN (audited) |
| POST | `/exams/{id}/subjects/auto` | Add every subject each class studies, with one max mark |
| GET | `/exams/{id}/publications` | Which sections are published |
| GET | `/dashboard/students?exam_id=&section_id=` | Drill-down: one section's results |
| GET | `/imports` · `/imports/{id}/errors.xlsx` | Import history and downloadable error list |
| GET/PUT | `/school/website`; POST `/school/website/images` | School admin edits the public school website and uploads photos |
| GET | `/public/schools/{code}/website` · `/public/schools/{code}/images/{id}` | Public school website and its photos |

**School website.** Each school gets a public site at `/schools/{CODE}`; set `HOME_SCHOOL_CODE` on the web server to show one school's site at `/` instead of the product page. Images must be ids of files uploaded to our own storage (stored under `site/{school_id}/`), so a school code can never serve another school's files and the page loads nothing from third parties. Social, map and WhatsApp links are validated (https only), and maps are a link, not an embedded iframe (no third-party tracking).

**Web.** The browser calls `/api/v1/*` on the Next.js origin, and Next rewrites it to the API, so the httpOnly `SameSite=Lax` refresh cookie works without cross-origin credentials. The access token is kept in memory only.

**Mobile.** The refresh token is stored with `flutter_secure_storage` (Android Keystore). FCM push is implemented on the server; to receive it, the app still needs the Firebase project files (`google-services.json`) and `firebase_messaging` registration (BUILD_PLAN 6.3).

## 15. Future (v2+) design hooks

Keep these in mind so v1 doesn't block them:

- `notifications` table + channels → WhatsApp/SMS later
- `modules` flag on `schools` → enable attendance, fees, homework per school
- `branding` JSON on `schools` → white-label app later
- i18n keys in web and app from day one (strings not hard-coded)
