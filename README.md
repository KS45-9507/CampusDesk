# CampusDesk College ERP

CampusDesk is a local college information system built with Python and SQLite. The new responsive web interface runs in a browser, requires no third-party packages, and keeps the existing desktop application available as an alternate interface.

## Deploy to Vercel (synthetic demo only)

This repository includes a Vercel Python WSGI entry point at `api/index.py` and root rewrite configuration. Push the project to GitHub, import it in Vercel, and deploy with the repository root as the project root.

In Vercel, add a Production environment variable named `CAMPUSDESK_SESSION_SECRET` with a fresh random value (for example, generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`). The app uses it to sign session cookies across serverless instances; never commit the value to GitHub.

**Important data limitation:** this version uses SQLite and in-process sessions. On Vercel, the database is placed under `/tmp`; it is disposable and can reset when an instance restarts, while in-memory sessions can disappear or differ between instances. Use this deployment only as a synthetic-data classroom/demo preview. Do not use real student information or collect real tuition payments. A reliable college deployment requires migrating SQLite to a managed PostgreSQL service and replacing in-memory sessions with a shared or signed stateless session design, plus institutional identity, HTTPS, and a security/privacy review.

The Vercel Python runtime supports WSGI apps and Vercel rewrites route requests to the Python function. See [Python runtime documentation](https://vercel.com/docs/functions/runtimes/python) and [rewrite configuration](https://vercel.com/docs/routing/rewrites).

## Start the web application locally

Requirements: Python 3.10 or newer. The web interface uses only the Python standard library.

```powershell
python main.py
```

On Windows, double-click `Run CampusDesk.bat`. It reuses a healthy local server or starts one on an available port, waits until the login page responds, and opens it in your browser. The minimized server window stays open while the app runs; close it to stop the server. Or start it manually in PowerShell with `python -u main.py` (or `py -3 -u main.py`) and open <http://127.0.0.1:8000>. The server listens on the local computer only. It uses `student_information.db` beside the Python files and preserves the existing demonstration records.

## Sign-in

The portal detects the account role after successful sign-in; there is no public role switch. Seeded local demo accounts are shown in the **Demo account access** section on the login page:

- Student: `OS2501` / `Campus@123` (student ID or college email works)
- Faculty: `faculty@campusdesk.edu` / `Faculty@123`
- Administrator: `admin@campusdesk.edu` / `Admin@123`

Passwords are stored as PBKDF2-SHA256 hashes. Sessions use an HttpOnly, SameSite cookie, CSRF tokens, an eight-hour expiry, and a fresh session ID after sign-in. These credentials are for the synthetic classroom demo only. A real college deployment needs an institutional identity provider, individual account provisioning and password resets, HTTPS, audit/security review, and appropriate privacy controls.

The earlier desktop prototype is still available if you need to compare it:

```powershell
python desktop_main.py
```

## ERP features

- **Overview dashboard:** student and course-record totals, marks overview, attendance warnings, recent activity, and campus notices.
- **Student directory:** add, search, and edit student profiles. Delete is restricted to the administrator role and protects the database’s linked-record rules.
- **Course catalog:** one course list for academic records, attendance, and term registration.
- **Marks and results:** faculty and administrators can add course marks and term attendance. Students can view only the selected demo profile’s results.
- **Class attendance:** record Present, Absent, Late, or Excused for a dated session. Present and Late count toward the attendance rate; Absent and Excused do not. Rates below 75% are flagged.
- **Course registration:** students can request a course for a term. Faculty or administrators can register, waitlist, complete, or withdraw a request. Duplicate student/course/term entries are prevented by SQLite.
- **Campus notices:** administrators publish updates for everyone, faculty, or students and set a priority.
- **CSV import:** administrators can load a group of students in one atomic transaction. Required columns are `student_id`, `full_name`, `program`, `semester`, and `email`; `phone` is optional. Duplicate IDs or emails reject the batch instead of partially importing it.
- **Printable course summary:** choose a student and open a print-ready report with course marks and attendance. Use the browser’s Print dialog to print or save a PDF.
- **Data tools:** administrators can download an academic-record CSV or a SQLite backup from the results page.
- **OS concepts:** real student, marks, registration, and attendance saves are recorded with process IDs, thread IDs, database transaction outcomes, and operation states. Scheduling comparisons remain clearly labeled simulations.

## Roles and demo data

Administrator, Faculty, and Student access is resolved from the authenticated account and each role has its own navigation and server-side action permissions. The local seeded accounts are demo credentials, not institutional identities. The app is bound to `127.0.0.1` and must not be exposed to a public network as a production system.

The bundled example names and academic records are synthetic. Use synthetic data only; do not enter real student personal or financial information into this project.

## Project files

- `main.py` — default web-app launcher
- `web_app.py` — local WSGI server, sign-in/session handling, routes, form handling, CSV import, and role checks
- `web_views.py` — accessible HTML views for dashboards, directory, courses, marks, attendance, registration, notices, reports, and OS traces
- `static/campusdesk.css` — responsive layout and print styles
- `static/erp-theme.css` — light-first aurora background, glass panels, optional dark mode, and refined ERP components
- `static/campusdesk.js` — CSV file loading and form interactions
- `database.py` — SQLite schema, demo account provisioning, PBKDF2 password verification, CRUD operations, attendance summaries, and OS operation tracing
- `desktop_main.py`, `app.py`, and `*_page.py` — optional Tkinter desktop interface
- `scheduler.py`, `models.py`, `concurrency_page.py`, and `os_lab_page.py` — scheduling and OS-concept demonstrations
- `student_information.db` — local demonstration database

## OS concepts demonstrated

| CampusDesk workflow | Operating-system concept |
| --- | --- |
| Save a student profile, marks, or attendance | Process/thread identifiers, process states, file/database I/O |
| Store changes in SQLite transactions | Atomicity and protected shared resources |
| Multiple application actions | Critical sections, mutual exclusion, and concurrency traces |
| Process scheduling comparison | FCFS, Round Robin, and Priority scheduling simulation |
| Concurrency learning area | Race conditions, bounded producer-consumer queue, process communication, Banker’s algorithm, and transaction rollback |

The OS lab is an educational model. It does not control the host operating system’s real scheduler or provide production security.
