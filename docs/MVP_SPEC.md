# MVP Spec: School Progress App (working name: VidyaTrack)

**Version:** 1.0 (draft) · **Owner:** Akiri Ashok Kumar · **Date:** 25 Oct 2026

This document says what version 1 does and what it does **not** do. Anything not listed under "In scope" is out of scope for v1.

---

## 1. Problem

Small and mid-size private schools in India share marks with parents on paper report cards, in WhatsApp groups or by phone. As a result:

- Parents only see marks 2–3 times a year and can't track progress between report cards.
- Principals have no quick view of which classes, subjects or students are falling behind.
- Teachers re-type the same marks into registers, Excel files and report cards.

## 2. Product in one sentence

A multi-school SaaS (web + Android) where teachers upload marks once, and principals, students and parents instantly see marks, report cards and progress.

## 3. Target customer (v1)

- Private CBSE / State-board schools in Telangana and Andhra Pradesh
- 200–1,500 students, 1 branch
- Currently using paper, Excel or a basic ERP without a good parent app
- Buyer: principal or correspondent/owner. Daily users: teachers and office staff.

## 4. Users and roles

| Role | Who | Main device | Can do |
|---|---|---|---|
| Platform admin | You (the company) | Web | Create schools, reset school admins, support |
| School admin | Office staff | Web | Set up academic year, classes, subjects, teachers, students, parents; bulk import; reset logins |
| Principal | Principal / owner | Web + app | See **all** marks, dashboards and reports for their school; publish results |
| Teacher | Class or subject teacher | Web + app | Enter / import marks **only** for the sections and subjects assigned to them |
| Student | Student | App + web | See **only their own** published marks, report cards and progress |
| Parent | Parent / guardian | App + web | See **only their own children's** published marks, report cards and progress |

A person can hold more than one role (e.g. a teacher who is also a parent). A parent can have multiple children, even across schools.

## 5. In scope for v1

### 5.1 Public website
- **Product landing page** (for selling): what it does, screenshots, pricing, "Book a demo" form, privacy policy, terms.
- **School page** (one per school, optional): school name, logo, address, contact, link to login.
- **Login page** that is simple, mobile-friendly and in English (Telugu/Hindi UI is v2).

### 5.2 Login and accounts
- Principal, school admin, teacher, parent: **phone number + OTP** login.
- Student: **school code + admission number + PIN** (many students don't have their own phone). The PIN is set by the school and can be reset by the school admin.
- Sessions stay logged in on the app (refresh tokens); users can log out.
- If a phone number is linked to several roles/schools, the user picks which one after login.

### 5.3 School setup (school admin)
- Academic year (e.g. 2026–27), marked as current.
- Classes (Nursery … 10) and sections (A, B, C).
- Subjects, and which subjects each class studies.
- Teachers, and which section + subject each teacher teaches. One class teacher per section.
- Students, with admission number, roll number, section, date of birth, gender.
- Parents, linked to students (father / mother / guardian), with phone numbers.
- **Bulk import from Excel/CSV** for students + parents and for teachers, using a downloadable template. Show a preview with row-level errors before saving.

### 5.4 Exams and marks
- School admin creates exams per academic year (e.g. Unit Test 1, Half-Yearly, Annual) and sets max marks per subject.
- Teacher enters marks for their section + subject:
  - in a grid on the web (student rows, one marks column), or
  - by Excel upload using a downloaded template pre-filled with student names.
- Special values: **AB** (absent), **EX** (exempted).
- Marks start as **Draft** (only staff can see them). Principal (or school admin) clicks **Publish** per exam + section. Only published marks are visible to students and parents.
- Grade is calculated from a per-school grade scale (default CBSE-style A1–E).
- Every create/change of a mark is logged (who, when, old value, new value).

### 5.5 Student and parent view
- List of exams with total, percentage, grade and rank-in-section (rank can be turned off per school).
- Subject-wise marks for each exam.
- **Progress chart**: percentage across exams this year, overall and per subject.
- **Report card PDF** download per exam, with school logo.
- Push notification when results are published.

### 5.6 Principal dashboard
- School overview for a chosen exam: students, average %, pass %, grade distribution.
- Class/section comparison: average % per section.
- Subject performance: average % per subject; weakest subjects.
- **Students needing attention**: below pass mark in 2+ subjects, or a drop of 10+ percentage points since the last exam.
- Toppers per section.
- Drill down: school → class → section → student.
- Marks entry status: which teachers have not yet submitted marks for an exam.
- Export any table to Excel.

### 5.7 Notifications (v1, minimal)
- Push notification (Firebase) to parents and students on results publish.
- OTP SMS only (no promotional SMS in v1).

### 5.8 Privacy and data protection (built in, not optional)
- Parent consent screen on first parent login (consent text supplied by the school; consent recorded with time and version).
- Role-based access enforced on the backend for every request.
- No ads, no third-party trackers, no selling of data.
- Data hosted in India.
- Audit log of logins and marks changes.

## 6. Out of scope for v1 (do NOT build yet)

- Fees and online payments
- Attendance
- Homework, notices, circulars, chat/messaging
- Timetable, transport, hostel, library, admissions/enquiries
- iOS app (Flutter makes it possible later)
- Telugu / Hindi interface
- School-branded app per school (white-label)
- WhatsApp integration
- AI features (report-card remarks, weak-topic analysis)
- Multi-branch / school-chain dashboards
- Online exams / question papers

These go into the v2 backlog (see `BUILD_PLAN.md`).

## 7. Key user flows

**F1: Onboard a new school (target: under 1 day)**
Platform admin creates school + school admin → school admin logs in → creates academic year, classes, sections, subjects → uploads students+parents Excel → uploads teachers Excel → assigns teachers to section+subject → principal account activated.

**F2: Teacher enters marks**
Teacher logs in → My classes → picks exam + section + subject → enters marks in the grid **or** downloads template, fills it, uploads → sees validation (e.g. marks > max) → Save draft → Submit.

**F3: Principal publishes results**
Principal opens exam → sees submission status per section/subject → reviews → Publish (whole exam or per section) → parents/students get a push notification.

**F4: Parent checks progress**
Parent installs app → enters phone → OTP → accepts consent (first time) → sees children → picks child → latest exam result → progress chart → downloads report card.

**F5: Student checks marks**
Student opens app → enters school code + admission no + PIN → sees own results and progress.

**F6: Principal monitors**
Principal logs in on web → dashboard for latest exam → clicks a weak section → sees students needing attention → exports list.

## 8. Screens

### Web (Next.js)
1. Landing page (public)
2. School page (public)
3. Login (OTP) / Student login
4. Role / school picker
5. **Admin:** academic year · classes & sections · subjects · teachers · students · parents · bulk import (upload → preview → commit) · teacher assignments · exams · grade scale · school profile
6. **Teacher:** my classes · marks entry grid · marks upload
7. **Principal:** dashboard · exam publish screen · section view · student profile · marks entry status
8. **Parent/Student:** results list · exam detail · progress chart · report card download
9. Consent screen · Profile / logout

### Android app (Flutter)
1. Login (OTP / student PIN)
2. Consent (parents)
3. Children list (parents with more than one child)
4. Home: latest result card + progress chart
5. Exams list → exam detail
6. Report card PDF viewer/download
7. Principal: dashboard (read-only summary) + students needing attention
8. Teacher: marks entry for one section + subject (simple list)
9. Notifications · Profile / logout

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Dashboard loads in < 2 s for a 1,500-student school; API p95 < 500 ms |
| Scale (year 1) | 50 schools, 50,000 students, 100,000 parents |
| Availability | 99.5% (exam-result days are peak load) |
| Mobile | Android 8+; works on cheap phones and slow 4G; app size < 25 MB |
| Security | HTTPS only; JWT with short expiry; OTP rate-limited; passwords/PINs hashed; tenant isolation tested |
| Data | Hosted in India (AWS Mumbai); daily backups kept 30 days; restore tested monthly |
| Privacy | DPDP-ready: consent records, data export/delete on school request, audit logs |
| Accessibility | Large fonts, high contrast, works for parents with low tech familiarity |

## 10. Success criteria for the pilot (one school term)

- 2–3 schools live, at least one using it for a full exam cycle.
- 100% of marks for one exam entered through the app.
- **≥ 60% of parents** log in at least once after results are published.
- Principal opens the dashboard at least weekly.
- School onboarding completed in ≤ 1 working day.
- At least 2 schools agree to pay for the next academic year.

## 11. Open questions (decide before or during the pilot)

1. Should rank be shown to parents by default? (Some schools avoid ranks.)
2. Do schools want co-scholastic grades (sports, art, conduct) on the report card in v1?
3. Do primary classes use grades only (no marks)?
4. Who pays for SMS OTPs: included in price, or capped?
5. Report card layout: one standard template, or per board (CBSE vs State)?
