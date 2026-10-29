"""Local CampusDesk web ERP, built only with the Python standard library."""

from __future__ import annotations

import csv
import base64
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import sys
import tempfile
import time
from datetime import date
from http import cookies
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode
from wsgiref.simple_server import make_server

from database import Database
from sample_data import sample_requests
from scheduler import simulate
import web_views as views


ROOT = Path(__file__).resolve().parent
# Vercel functions have a read-only deployment bundle. /tmp is writable there,
# but is intentionally treated as disposable demo storage; local runs keep the
# familiar database beside the project files.
DB_PATH = Path(os.environ.get("CAMPUSDESK_DB_PATH", str(ROOT / "student_information.db")))
if os.environ.get("VERCEL") and "CAMPUSDESK_DB_PATH" not in os.environ:
    DB_PATH = Path(tempfile.gettempdir()) / "campusdesk-demo.db"
ROLES = {"Administrator", "Faculty", "Student"}
SESSION_SECRET = os.environ.get("CAMPUSDESK_SESSION_SECRET", "")
if os.environ.get("VERCEL") and not SESSION_SECRET:
    raise RuntimeError("Set CAMPUSDESK_SESSION_SECRET in the Vercel project environment variables.")
if not SESSION_SECRET:
    # Local development only. Restarting the local process signs everyone out.
    SESSION_SECRET = secrets.token_urlsafe(48)
SESSION_SECRET_BYTES = SESSION_SECRET.encode("utf-8")
MAX_BODY = 1_500_000


def _field(form: dict[str, list[str]], name: str, default: str = "") -> str:
    return (form.get(name, [default])[0] or default).strip()


def _session(environ):
    jar = cookies.SimpleCookie()
    try:
        jar.load(environ.get("HTTP_COOKIE", ""))
    except cookies.CookieError:
        pass
    key = jar.get("campusdesk_session")
    if key:
        try:
            encoded, supplied_signature = key.value.rsplit(".", 1)
            expected_signature = hmac.new(SESSION_SECRET_BYTES, encoded.encode("ascii"), hashlib.sha256).hexdigest()
            if hmac.compare_digest(supplied_signature, expected_signature):
                padded = encoded + "=" * (-len(encoded) % 4)
                claims = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
                if float(claims.get("expires_at", 0)) >= time.time():
                    session = {name: claims.get(name, "") for name in
                               ("role", "student_id", "display_name", "login_name", "authenticated", "csrf", "sid")}
                    session["expires_at"] = float(claims["expires_at"])
                    session["_sid"] = session.pop("sid")
                    return session["_sid"], session, False
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeError):
            pass
    sid = secrets.token_urlsafe(24)
    session = {"role": "", "student_id": "", "display_name": "", "login_name": "", "authenticated": False,
               "csrf": secrets.token_urlsafe(24), "expires_at": time.time() + 28_800, "_sid": sid}
    return sid, session, True


def _parse_form(environ) -> dict[str, list[str]]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        length = 0
    if length > MAX_BODY:
        raise ValueError("This form is too large. Keep CSV imports under 1.5 MB.")
    body = environ["wsgi.input"].read(length).decode("utf-8-sig", errors="replace")
    return parse_qs(body, keep_blank_values=True, max_num_fields=10_000)


def _response(start_response, body: str | bytes, status="200 OK", content_type="text/html; charset=utf-8", extra_headers=None):
    payload = body if isinstance(body, bytes) else body.encode("utf-8")
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(payload))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "same-origin"),
        ("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(status, headers)
    return [payload]


def _cookie(sid):
    return ("Set-Cookie", f"campusdesk_session={sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800")


def _redirect(start_response, sid, location, new_session=False):
    headers = [("Location", location), ("Cache-Control", "no-store")]
    if new_session:
        headers.append(_cookie(sid))
    start_response("303 See Other", headers)
    return [b""]


def _html_response(start_response, body, title, role, session, students, active, status="200 OK", notice="", new_session=False):
    page = views.shell(title, body, role=role, student_id=session.get("student_id", ""), students=students,
                       active=active, token=session["csrf"], display_name=session.get("display_name", "Campus user"), notice=notice)
    headers = [_cookie_for_session(session)] if new_session else None
    return _response(start_response, page, status, extra_headers=headers)


def _cookie_for_session(session):
    claims = {name: session.get(name, "") for name in
              ("role", "student_id", "display_name", "login_name", "authenticated", "csrf")}
    claims["sid"] = session["_sid"]
    claims["expires_at"] = int(session.get("expires_at", time.time() + 28_800))
    encoded = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8")).rstrip(b"=").decode("ascii")
    signature = hmac.new(SESSION_SECRET_BYTES, encoded.encode("ascii"), hashlib.sha256).hexdigest()
    secure = "; Secure" if os.environ.get("VERCEL") else ""
    return ("Set-Cookie", f"campusdesk_session={encoded}.{signature}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800{secure}")


def _forbidden(start_response, sid, session, role, students, new_session=False):
    body = '<section class="panel"><h3>This page is not available to your account</h3><p>Contact your campus administrator if you need access.</p></section>'
    return _html_response(start_response, body, "Access unavailable", role, session, students, "", "403 Forbidden",
                          new_session=new_session)


def _validate_student(form):
    student_id = _field(form, "student_id").upper()
    name = _field(form, "full_name")
    program = _field(form, "program")
    email = _field(form, "email").lower()
    phone = _field(form, "phone")
    semester = int(_field(form, "semester", "0"))
    if not student_id or not name or not program or not email:
        raise ValueError("Enter the student ID, name, program, semester, and email.")
    if semester < 1 or semester > 12:
        raise ValueError("Semester must be between 1 and 12.")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return {"student_id": student_id, "full_name": name, "program": program,
            "semester": semester, "email": email, "phone": phone}


def _import_csv(text: str, db: Database) -> int:
    reader = csv.DictReader(io.StringIO(text))
    required = {"student_id", "full_name", "program", "semester", "email"}
    if not reader.fieldnames:
        raise ValueError("Choose a CSV file or paste CSV text first.")
    headings = {name.strip().lower() for name in reader.fieldnames if name}
    missing = sorted(required - headings)
    if missing:
        raise ValueError("CSV is missing required columns: " + ", ".join(missing))
    mapping = {name.strip().lower(): name for name in reader.fieldnames if name}
    rows = []
    seen_ids, seen_emails = set(), set()
    for line, record in enumerate(reader, start=2):
        if not any((value or "").strip() for value in record.values()):
            continue
        student_id = (record.get(mapping["student_id"]) or "").strip().upper()
        name = (record.get(mapping["full_name"]) or "").strip()
        program = (record.get(mapping["program"]) or "").strip()
        email = (record.get(mapping["email"]) or "").strip().lower()
        phone = (record.get(mapping.get("phone", "")) or "").strip()
        try:
            semester = int((record.get(mapping["semester"]) or "").strip())
        except ValueError as exc:
            raise ValueError(f"Row {line}: semester must be a whole number from 1 to 12.") from exc
        if not student_id or not name or not program or "@" not in email:
            raise ValueError(f"Row {line}: enter an ID, name, program, and valid email.")
        if not 1 <= semester <= 12:
            raise ValueError(f"Row {line}: semester must be between 1 and 12.")
        if student_id in seen_ids or email in seen_emails:
            raise ValueError(f"Row {line}: duplicate student ID or email in this file.")
        seen_ids.add(student_id)
        seen_emails.add(email)
        rows.append((student_id, name, program, semester, email, phone))
        if len(rows) > 1000:
            raise ValueError("Import up to 1,000 students at a time.")
    if not rows:
        raise ValueError("The CSV contains no student rows to import.")
    return db.import_students(rows)


class CampusDeskApplication:
    def __init__(self):
        self.db = Database(DB_PATH)

    def __call__(self, environ, start_response):
        sid, session, new_session = _session(environ)
        session["_sid"] = sid
        response_start = start_response

        def start_response(status, headers, exc_info=None):
            headers = [(name, value) for name, value in headers if name.lower() != "set-cookie"]
            headers.append(_cookie_for_session(session))
            return response_start(status, headers, exc_info)

        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        if path.startswith("/static/"):
            assets = {"/static/campusdesk.css": (ROOT / "static" / "campusdesk.css", "text/css; charset=utf-8"),
                      "/static/aurora-glass.css": (ROOT / "static" / "aurora-glass.css", "text/css; charset=utf-8"),
                      "/static/erp-theme.css": (ROOT / "static" / "erp-theme.css", "text/css; charset=utf-8"),
                      "/static/campusdesk.js": (ROOT / "static" / "campusdesk.js", "text/javascript; charset=utf-8")}
            item = assets.get(path)
            if not item:
                return _response(start_response, "Not found", "404 Not Found", "text/plain; charset=utf-8")
            return _response(start_response, item[0].read_bytes(), content_type=item[1])

        try:
            if method == "POST":
                form = _parse_form(environ)
                if not secrets.compare_digest(_field(form, "csrf"), session["csrf"]):
                    return _response(start_response, "Form expired. Reload the page and try again.", "400 Bad Request")
            else:
                form = {}
            query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
            db = self.db
            if path == "/login":
                if session.get("authenticated"):
                    return _redirect(start_response, sid, "/")
                if method == "POST":
                    login_name = _field(form, "login_name")
                    password = form.get("password", [""])[0]
                    account = db.authenticate_portal_user(login_name, password)
                    if not account:
                        page = views.login_page(session["csrf"], "We couldn’t sign you in. Check your ID or email and password, then try again.")
                        headers = [_cookie(sid)] if new_session else None
                        return _response(start_response, page, "401 Unauthorized", extra_headers=headers)
                    sid = secrets.token_urlsafe(32)
                    session.update({"role": account["role"], "student_id": account["student_id"],
                                    "display_name": account["display_name"], "login_name": account["login_name"],
                                    "authenticated": True, "csrf": secrets.token_urlsafe(24), "_sid": sid,
                                    "expires_at": time.time() + 28_800})
                    return _redirect(start_response, sid, "/", True)
                page = views.login_page(session["csrf"], (query.get("error") or [""])[0])
                headers = [_cookie(sid)] if new_session else None
                return _response(start_response, page, extra_headers=headers)
            if path == "/logout" and method == "POST" and session.get("authenticated"):
                sid = secrets.token_urlsafe(32)
                session = {"role": "", "student_id": "", "display_name": "", "authenticated": False,
                           "login_name": "", "csrf": secrets.token_urlsafe(24), "_sid": sid,
                           "expires_at": time.time() + 28_800}
                return _redirect(start_response, sid, "/login", True)
            if not session.get("authenticated"):
                return _redirect(start_response, sid, "/login", new_session)
            role = session.get("role", "")
            if role not in ROLES:
                session["authenticated"] = False
                return _redirect(start_response, sid, "/login", new_session)
            choices = db.list_student_choices()
            choice_ids = {item[0] for item in choices}
            if role == "Student" and session.get("student_id") not in choice_ids:
                session["authenticated"] = False
                return _redirect(start_response, sid, "/login", new_session)
            if role != "Student" and session.get("student_id") not in choice_ids:
                session["student_id"] = choices[0][0] if choices else ""
            db.set_access_context(role, session.get("student_id", ""))
            students = choices
            courses = db.list_courses()

            if method == "POST":
                action = path
                try:
                    if action == "/students/save":
                        if role != "Administrator":
                            raise PermissionError("Only administrators can change student profiles.")
                        data = _validate_student(form)
                        db.save_student(data, _field(form, "original_id") or None)
                        return _redirect(start_response, sid, "/students?" + urlencode({"notice": "Student profile saved."}), new_session)
                    if action == "/students/delete":
                        if role != "Administrator":
                            raise PermissionError("Only administrators can remove student profiles.")
                        db.delete_student(_field(form, "student_id"))
                        return _redirect(start_response, sid, "/students?" + urlencode({"notice": "Student profile removed."}), new_session)
                    if action == "/import":
                        if role != "Administrator":
                            raise PermissionError("Only administrators can import student records.")
                        count = _import_csv(_field(form, "csv_data"), db)
                        return _redirect(start_response, sid, "/students?" + urlencode({"notice": f"Imported {count} student profile(s)."}), new_session)
                    if action == "/courses/save":
                        if role != "Administrator":
                            raise PermissionError("Only administrators can add courses.")
                        data = {"course_code": _field(form, "course_code").upper(), "course_name": _field(form, "course_name"),
                                "department": _field(form, "department"), "credits": int(_field(form, "credits", "0")),
                                "semester": int(_field(form, "semester", "0"))}
                        if not all(data[k] for k in ("course_code", "course_name", "department")) or not 1 <= data["credits"] <= 10 or not 1 <= data["semester"] <= 12:
                            raise ValueError("Enter a course code, name, department, 1–10 credits, and semester 1–12.")
                        db.save_course(data)
                        return _redirect(start_response, sid, "/courses?" + urlencode({"notice": "Course added to the catalog."}), new_session)
                    if action == "/records/save":
                        if role not in {"Administrator", "Faculty"}:
                            raise PermissionError("Students can view their marks but cannot enter them.")
                        code = _field(form, "course_code").upper()
                        course = next((row for row in db.list_courses() if row["course_code"] == code), None)
                        if not course:
                            raise ValueError("Choose a course from the catalog.")
                        marks, attendance = float(_field(form, "marks")), float(_field(form, "attendance"))
                        if not 0 <= marks <= 100 or not 0 <= attendance <= 100:
                            raise ValueError("Marks and attendance must be from 0 to 100.")
                        data = {"student_id": _field(form, "student_id"), "course_code": code,
                                "course_name": course["course_name"], "term": _field(form, "term"),
                                "attendance": attendance, "marks": marks}
                        if not data["student_id"] or not data["term"]:
                            raise ValueError("Choose a student and enter the academic term.")
                        db.save_record(data)
                        return _redirect(start_response, sid, "/records?" + urlencode({"notice": "Course results saved."}), new_session)
                    if action == "/attendance/save":
                        if role not in {"Administrator", "Faculty"}:
                            raise PermissionError("Students can view their attendance but cannot change it.")
                        student_id, code = _field(form, "student_id"), _field(form, "course_code").upper()
                        session_date, status = _field(form, "session_date"), _field(form, "status")
                        try:
                            date.fromisoformat(session_date)
                        except ValueError as exc:
                            raise ValueError("Class date must use YYYY-MM-DD.") from exc
                        if not student_id or not code or status not in {"Present", "Absent", "Late", "Excused"}:
                            raise ValueError("Choose a student, course, date, and attendance status.")
                        db.save_session_attendance({"student_id": student_id, "course_code": code,
                                                    "session_date": session_date, "status": status})
                        return _redirect(start_response, sid, "/attendance?" + urlencode({"notice": "Class attendance saved."}), new_session)
                    if action == "/registration/save":
                        student_id = session.get("student_id", "") if role == "Student" else _field(form, "student_id")
                        data = {"student_id": student_id, "course_code": _field(form, "course_code").upper(),
                                "term": _field(form, "term"), "status": "Requested" if role == "Student" else _field(form, "status", "Registered")}
                        if not data["student_id"] or not data["course_code"] or not data["term"]:
                            raise ValueError("Choose a student and course, and enter the term.")
                        db.save_registration(data)
                        return _redirect(start_response, sid, "/registration?" + urlencode({"notice": "Course request saved." if role == "Student" else "Course registration saved."}), new_session)
                    if action == "/registration/status":
                        if role not in {"Administrator", "Faculty"}:
                            raise PermissionError("Only staff can change registration status.")
                        db.update_registration_status(int(_field(form, "registration_id")), _field(form, "status"))
                        return _redirect(start_response, sid, "/registration?" + urlencode({"notice": "Registration status updated."}), new_session)
                    if action == "/notices/save":
                        if role != "Administrator":
                            raise PermissionError("Only administrators can publish campus notices.")
                        title, body = _field(form, "title"), _field(form, "body")
                        if not title or not body or len(title) > 120 or len(body) > 2000:
                            raise ValueError("Enter a title (up to 120 characters) and a message (up to 2,000 characters).")
                        db.create_notice(title, body, _field(form, "audience"), _field(form, "priority"))
                        return _redirect(start_response, sid, "/notices?" + urlencode({"notice": "Campus notice published."}), new_session)
                    return _response(start_response, "Not found", "404 Not Found")
                except (ValueError, PermissionError, sqlite3.IntegrityError) as exc:
                    message = str(exc)
                    if isinstance(exc, sqlite3.IntegrityError):
                        message = "That ID, email, course, term, or session already exists. Check the details and try again."
                    return _redirect(start_response, sid, path + "?" + urlencode({"error": message}), new_session)

            db.set_access_context(role, session.get("student_id", ""))
            notice = (query.get("notice") or [""])[0]
            error = (query.get("error") or [""])[0]
            if error:
                notice = error
            if path == "/":
                summary = db.summary()
                performance = db.course_performance_summary()
                attendance = db.session_attendance_summary()
                recent = summary["recent"] if role == "Administrator" else []
                current_student = db.get_student(session.get("student_id", "")) if role == "Student" else None
                body = views.dashboard_page(role, summary, performance, attendance, db.visible_notices(), recent, current_student)
                return _html_response(start_response, body, "Overview", role, session, students, "/", notice=notice, new_session=new_session)
            if path == "/fees":
                if role != "Student":
                    return _forbidden(start_response, sid, session, role, students, new_session)
                current_student = db.get_student(session.get("student_id", ""))
                return _html_response(start_response, views.fees_page(current_student), "Tuition & fees", role, session, students, "/fees", notice=notice, new_session=new_session)
            if path == "/students":
                editing = None
                edit_id = (query.get("edit") or [""])[0]
                if edit_id and role == "Administrator":
                    found = db.get_student(edit_id)
                    editing = dict(found) if found else None
                rows = db.list_students((query.get("q") or [""])[0])
                body = views.students_page(rows, role, (query.get("q") or [""])[0], session["csrf"], editing)
                return _html_response(start_response, body, "Students", role, session, students, "/students", notice=notice, new_session=new_session)
            if path == "/import":
                if role != "Administrator":
                    return _forbidden(start_response, sid, session, role, students, new_session)
                return _html_response(start_response, views.import_page(session["csrf"]), "Import students", role, session, students, "/import", notice=notice, new_session=new_session)
            if path == "/courses":
                if role == "Student":
                    return _forbidden(start_response, sid, session, role, students, new_session)
                body = views.courses_page(db.list_courses((query.get("q") or [""])[0]), role,
                                          (query.get("q") or [""])[0], session["csrf"])
                return _html_response(start_response, body, "Course catalog", role, session, students, "/courses", notice=notice, new_session=new_session)
            if path == "/records":
                rows = db.list_records((query.get("q") or [""])[0])
                body = views.records_page(rows, role, (query.get("q") or [""])[0], db.list_students(), courses, session["csrf"])
                return _html_response(start_response, body, "Marks & results", role, session, students, "/records", notice=notice, new_session=new_session)
            if path == "/attendance":
                rows = db.list_session_attendance(student_id=session.get("student_id", "") if role == "Student" else "")
                summaries = db.session_attendance_summary()
                body = views.attendance_page(rows[:100], summaries, role, db.list_students(), courses, session["csrf"])
                return _html_response(start_response, body, "Attendance", role, session, students, "/attendance", notice=notice, new_session=new_session)
            if path == "/registration":
                rows = db.list_registrations()
                body = views.registration_page(rows, role, db.list_students(), courses, session["csrf"], session.get("student_id", ""))
                return _html_response(start_response, body, "Course registration", role, session, students, "/registration", notice=notice, new_session=new_session)
            if path == "/notices":
                body = views.notices_page(db.visible_notices(), role, session["csrf"])
                return _html_response(start_response, body, "Campus notices", role, session, students, "/notices", notice=notice, new_session=new_session)
            if path == "/reports":
                selected = (query.get("student_id") or [""])[0]
                if role == "Student":
                    selected = session.get("student_id", "")
                if selected:
                    student = db.get_student(selected)
                    if student:
                        records = db.list_records_for(student_id=selected)
                        summaries = db.session_attendance_summary(selected)
                        return _html_response(start_response, views.transcript_page(student, records, summaries),
                                              "Student course summary", role, session, students, "/reports", notice=notice, new_session=new_session)
                body = views.reports_page(role, db.list_students(), selected)
                return _html_response(start_response, body, "Student reports", role, session, students, "/reports", notice=notice, new_session=new_session)
            if path.startswith("/reports/"):
                if role not in ROLES:
                    return _forbidden(start_response, sid, session, role, students, new_session)
                student_id = path.removeprefix("/reports/")
                student = db.get_student(student_id)
                if not student:
                    return _response(start_response, "Student report not found for this workspace.", "404 Not Found")
                records = db.list_records_for(student_id=student_id)
                summaries = db.session_attendance_summary(student_id)
                return _html_response(start_response, views.transcript_page(student, records, summaries),
                                      "Student course summary", role, session, students, "/reports", new_session=new_session)
            if path == "/export.csv":
                if role != "Administrator":
                    return _forbidden(start_response, sid, session, role, students, new_session)
                with tempfile.TemporaryDirectory(prefix="campusdesk-export-") as folder:
                    target = Path(folder) / "campusdesk_academic_records.csv"
                    db.export_academic_records(target)
                    payload = target.read_bytes()
                return _response(start_response, payload, content_type="text/csv; charset=utf-8",
                                 extra_headers=[("Content-Disposition", 'attachment; filename="campusdesk_academic_records.csv"')])
            if path == "/backup.db":
                if role != "Administrator":
                    return _forbidden(start_response, sid, session, role, students, new_session)
                with tempfile.TemporaryDirectory(prefix="campusdesk-backup-") as folder:
                    target = Path(folder) / "student_information_backup.db"
                    db.create_backup(target)
                    payload = target.read_bytes()
                return _response(start_response, payload, content_type="application/vnd.sqlite3",
                                 extra_headers=[("Content-Disposition", 'attachment; filename="student_information_backup.db"')])
            if path == "/os-lab":
                if role == "Student":
                    return _forbidden(start_response, sid, session, role, students, new_session)
                operations = db.recent_operations(15)
                event_map = {op["operation_id"]: db.operation_events(op["operation_id"]) for op in operations}
                workload = sample_requests()
                scheduling = []
                for algorithm in ("FCFS", "Round Robin", "Priority"):
                    result = simulate(workload, algorithm)
                    scheduling.append((algorithm, result.average_wait, result.average_turnaround))
                body = views.os_lab_page(operations, event_map, scheduling)
                return _html_response(start_response, body, "OS concepts", role, session, students, "/os-lab", notice=notice, new_session=new_session)
            return _response(start_response, "Not found", "404 Not Found")
        except ValueError as exc:
            return _response(start_response, str(exc), "400 Bad Request")
        except Exception:
            # Keep local application details and file paths out of browser error pages.
            return _response(start_response, "CampusDesk could not load this page. Return to Overview and try again.", "500 Internal Server Error")


application = CampusDeskApplication()


def main():
    host = os.environ.get("CAMPUSDESK_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("PORT must be a number from 1 to 65535.", file=sys.stderr, flush=True)
        raise SystemExit(2)

    address = (host, port)
    try:
        server = make_server(*address, application)
    except OSError as exc:
        if exc.errno in (48, 98, 10048):
            print(f"CampusDesk could not start: port {port} is already in use. "
                  "Close the other server or choose another port with PORT=8001.",
                  file=sys.stderr, flush=True)
        else:
            print(f"CampusDesk could not bind to {host}:{port}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc

    with server:
        shown_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
        print(f"CampusDesk web app running at http://{shown_host}:{port}", flush=True)
        print("Keep this terminal open while using the portal. Press Ctrl+C to stop.", flush=True)
        if host != "0.0.0.0":
            print("Demo authentication is enabled. Keep this prototype on the local computer only.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nCampusDesk web app stopped.", flush=True)


if __name__ == "__main__":
    main()
