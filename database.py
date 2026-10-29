"""SQLite storage for the local university student information system."""

from pathlib import Path
import sqlite3
from datetime import datetime
import hashlib
import hmac
import secrets
import csv
import os
import threading
from sample_data import DEMO_COURSES, DEMO_SESSIONS, DEMO_STUDENTS


class Database:
    def __init__(self, path: str | Path = "student_information.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._database_lock = threading.Lock()
        self.active_role = "Administrator"
        self.active_student_id = ""
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    program TEXT NOT NULL,
                    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 12),
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS portal_accounts (
                    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('Administrator', 'Faculty', 'Student')),
                    student_id TEXT UNIQUE REFERENCES students(student_id) ON DELETE CASCADE,
                    display_name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS academic_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
                    course_code TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    term TEXT NOT NULL,
                    attendance REAL NOT NULL CHECK (attendance BETWEEN 0 AND 100),
                    marks REAL NOT NULL CHECK (marks BETWEEN 0 AND 100),
                    UNIQUE(student_id, course_code, term)
                );
                CREATE TABLE IF NOT EXISTS courses (
                    course_code TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    credits INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 10),
                    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 12)
                );
                CREATE TABLE IF NOT EXISTS session_attendance (
                    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
                    course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
                    session_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('Present', 'Absent', 'Late', 'Excused')),
                    UNIQUE(student_id, course_code, session_date)
                );
                CREATE TABLE IF NOT EXISTS activity_log (
                    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    happened_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS os_operations (
                    operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    os_pid INTEGER NOT NULL,
                    thread_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    actor_role TEXT NOT NULL DEFAULT 'Administrator',
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                );
                CREATE TABLE IF NOT EXISTS os_operation_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id INTEGER NOT NULL REFERENCES os_operations(operation_id) ON DELETE CASCADE,
                    state TEXT NOT NULL,
                    details TEXT NOT NULL,
                    happened_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS course_registrations (
                    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
                    course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
                    term TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Requested'
                        CHECK (status IN ('Requested','Registered','Waitlisted','Completed','Withdrawn')),
                    created_at TEXT NOT NULL,
                    UNIQUE(student_id, course_code, term)
                );
                CREATE TABLE IF NOT EXISTS campus_notices (
                    notice_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL UNIQUE,
                    body TEXT NOT NULL,
                    audience TEXT NOT NULL DEFAULT 'All'
                        CHECK (audience IN ('All','Faculty','Students')),
                    priority TEXT NOT NULL DEFAULT 'Normal'
                        CHECK (priority IN ('Normal','Important','Urgent')),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL DEFAULT 'Administrator'
                );
            """)
            operation_columns = {row["name"] for row in con.execute("PRAGMA table_info(os_operations)")}
            if "actor_role" not in operation_columns:
                con.execute("ALTER TABLE os_operations ADD COLUMN actor_role TEXT NOT NULL DEFAULT 'Administrator'")
            count = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            con.execute("""INSERT OR IGNORE INTO courses (course_code, course_name, department, credits, semester)
                SELECT DISTINCT course_code, course_name, 'Computer Science', 4, 3 FROM academic_records""")
            # Existing academic records represent completed course registrations.
            con.execute("""INSERT OR IGNORE INTO course_registrations
                (student_id, course_code, term, status, created_at)
                SELECT student_id, course_code, term, 'Completed', ? FROM academic_records""",
                (datetime.now().astimezone().isoformat(timespec="seconds"),))
            # Add example campus notices only to the marked synthetic starter database.
            if con.execute("SELECT 1 FROM students WHERE email='aarav.demo@example.edu'").fetchone():
                seeded_at = datetime.now().astimezone().isoformat(timespec="seconds")
                con.executemany("""INSERT OR IGNORE INTO campus_notices
                    (title, body, audience, priority, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)""", [
                    ("Course registration help", "Review your semester course list and contact your faculty coordinator if a required course is missing.", "Students", "Important", seeded_at, "Administrator"),
                    ("Attendance support", "Students below the attendance requirement should speak with the course instructor early.", "All", "Important", seeded_at, "Administrator"),
                    ("Marks entry reminder", "Faculty can review pending course marks and confirm that every class section has been updated.", "Faculty", "Normal", seeded_at, "Administrator"),
                ])
            if count == 0:
                con.executemany("""INSERT INTO students
                    (student_id, full_name, program, semester, email, phone) VALUES (?, ?, ?, ?, ?, ?)""", [
                    ("OS2501", "Aarav Sharma", "B.Tech CSE", 3, "aarav.demo@example.edu", "9000000001"),
                    ("OS2502", "Diya Verma", "B.Tech CSE", 3, "diya.demo@example.edu", "9000000002"),
                    ("OS2503", "Kabir Mehta", "B.Tech IT", 5, "kabir.demo@example.edu", "9000000003"),
                ])
                con.executemany("""INSERT INTO academic_records
                    (student_id, course_code, course_name, term, attendance, marks) VALUES (?, ?, ?, ?, ?, ?)""", [
                    ("OS2501", "CCSE0303A", "Operating System", "Semester 3", 88, 82),
                    ("OS2502", "CCSE0303A", "Operating System", "Semester 3", 94, 91),
                    ("OS2503", "CCSE0303A", "Operating System", "Semester 5", 79, 74),
                ])
                self._log(con, "Setup", "Created the synthetic demonstration dataset")
            # Expand only the clearly marked starter dataset; never add demo people to an unrelated database.
            if con.execute("SELECT 1 FROM students WHERE email='aarav.demo@example.edu'").fetchone():
                con.executemany("""INSERT OR IGNORE INTO students
                    (student_id, full_name, program, semester, email, phone) VALUES (?, ?, ?, ?, ?, ?)""", DEMO_STUDENTS)
                con.executemany("""INSERT OR IGNORE INTO courses
                    (course_code, course_name, department, credits, semester) VALUES (?, ?, ?, ?, ?)""", DEMO_COURSES)
                course_codes = [row[0] for row in DEMO_COURSES]
                all_demo_students = [
                    ("OS2501", "aarav.demo@example.edu"), ("OS2502", "diya.demo@example.edu"),
                    ("OS2503", "kabir.demo@example.edu"),
                    *[(student[0], student[4]) for student in DEMO_STUDENTS],
                ]
                for student_index, (student_id, expected_email) in enumerate(all_demo_students):
                    student_row = con.execute("SELECT semester, email FROM students WHERE student_id=?", (student_id,)).fetchone()
                    if not student_row or student_row["email"] != expected_email:
                        continue
                    term = f"Semester {student_row['semester']}"
                    chosen_courses = [course_codes[(student_index + offset) % len(course_codes)] for offset in range(3)]
                    for course_index, course_code in enumerate(chosen_courses):
                        course = con.execute("SELECT course_name FROM courses WHERE course_code=?", (course_code,)).fetchone()
                        marks = 58 + ((student_index * 13 + course_index * 17) % 41)
                        legacy_attendance = 62 + ((student_index * 19 + course_index * 11) % 39)
                        con.execute("""INSERT OR IGNORE INTO academic_records
                            (student_id, course_code, course_name, term, attendance, marks) VALUES (?, ?, ?, ?, ?, ?)""",
                            (student_id, course_code, course["course_name"], term, legacy_attendance, marks))
                        for date_index, session_date in enumerate(DEMO_SESSIONS):
                            pattern = (student_index + course_index + date_index) % 7
                            status = "Absent" if pattern == 0 else "Excused" if pattern == 1 else "Late" if pattern == 2 else "Present"
                            con.execute("""INSERT OR IGNORE INTO session_attendance
                                (student_id, course_code, session_date, status) VALUES (?, ?, ?, ?)""",
                                (student_id, course_code, session_date, status))
            con.execute("""INSERT OR IGNORE INTO courses (course_code, course_name, department, credits, semester)
                SELECT DISTINCT course_code, course_name, 'Computer Science', 4, 3 FROM academic_records""")
            if con.execute("SELECT 1 FROM students WHERE email='aarav.demo@example.edu'").fetchone():
                self._seed_demo_accounts(con)

    @staticmethod
    def _make_password_hash(password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        iterations = 260_000
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"

    @classmethod
    def _seed_demo_accounts(cls, con: sqlite3.Connection) -> None:
        created = datetime.now().astimezone().isoformat(timespec="seconds")
        staff = [
            ("admin@campusdesk.edu", "Admin@123", "Administrator", None, "Campus Administrator"),
            ("faculty@campusdesk.edu", "Faculty@123", "Faculty", None, "Demo Faculty"),
        ]
        for login, password, role, student_id, name in staff:
            if not con.execute("SELECT 1 FROM portal_accounts WHERE login_name=?", (login,)).fetchone():
                con.execute("""INSERT INTO portal_accounts
                    (login_name, password_hash, role, student_id, display_name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (login, cls._make_password_hash(password), role, student_id, name, created))
        students = con.execute("SELECT student_id, full_name FROM students ORDER BY student_id").fetchall()
        for student in students:
            if not con.execute("SELECT 1 FROM portal_accounts WHERE student_id=?", (student["student_id"],)).fetchone():
                con.execute("""INSERT INTO portal_accounts
                    (login_name, password_hash, role, student_id, display_name, created_at)
                    VALUES (?, ?, 'Student', ?, ?, ?)""",
                    (student["student_id"], cls._make_password_hash("Campus@123"),
                     student["student_id"], student["full_name"], created))

    def authenticate_portal_user(self, login_name: str, password: str) -> dict[str, str] | None:
        login = login_name.strip()
        with self.connect() as con:
            account = con.execute("""SELECT a.* FROM portal_accounts a
                LEFT JOIN students s ON s.student_id=a.student_id
                WHERE a.is_active=1 AND (a.login_name=? COLLATE NOCASE OR s.email=? COLLATE NOCASE)
                LIMIT 1""", (login, login)).fetchone()
        encoded = account["password_hash"] if account else ""
        valid = False
        try:
            algorithm, rounds, salt_hex, expected = encoded.split("$", 3)
            if algorithm == "pbkdf2_sha256":
                actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)).hex()
                valid = hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"campusdesk-demo-salt", 260_000)
        if not account or not valid:
            return None
        return {"role": account["role"], "student_id": account["student_id"] or "",
                "display_name": account["display_name"], "login_name": account["login_name"]}

    @staticmethod
    def _log(con: sqlite3.Connection, action: str, details: str) -> None:
        con.execute("INSERT INTO activity_log (happened_at, action, details) VALUES (?, ?, ?)",
                    (datetime.now().astimezone().isoformat(timespec="seconds"), action, details))

    def set_access_context(self, role: str, student_id: str = "") -> None:
        self.active_role = role
        self.active_student_id = student_id

    def _require_role(self, *allowed_roles: str) -> None:
        if self.active_role not in allowed_roles:
            raise PermissionError(f"{self.active_role} does not have permission for this action.")

    @staticmethod
    def _event(con: sqlite3.Connection, operation_id: int, state: str, details: str) -> None:
        con.execute("INSERT INTO os_operation_events (operation_id, state, details, happened_at) VALUES (?, ?, ?, ?)",
                    (operation_id, state, details, datetime.now().astimezone().isoformat(timespec="seconds")))

    def _run_operation(self, action: str, details: str, work) -> int:
        """Run one real SIS action as a traced process with a locked DB critical section."""
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        # Record New/Ready before waiting for the shared database lock so concurrent
        # workers can be seen waiting for the critical section.
        with self.connect() as con:
            cursor = con.execute("""INSERT INTO os_operations
                (os_pid, thread_id, action, details, actor_role, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (os.getpid(), threading.get_ident(), action, details,
                                                     self.active_role, "Ready", now))
            operation_id = cursor.lastrowid
            self._event(con, operation_id, "New", "The user started this operation.")
            self._event(con, operation_id, "Ready", "Waiting to use the shared database.")

        try:
            with self._database_lock:
                with self.connect() as con:
                    self._event(con, operation_id, "Running", "Entered the database critical section.")
                    work(con)
                    self._log(con, action, details)
                    self._event(con, operation_id, "Terminated", "The database transaction finished successfully.")
                    con.execute("UPDATE os_operations SET status=?, ended_at=? WHERE operation_id=?",
                                ("Completed", datetime.now().astimezone().isoformat(timespec="seconds"), operation_id))
            return operation_id
        except Exception:
            with self.connect() as con:
                self._event(con, operation_id, "Failed", "The change could not be saved, so the transaction was rolled back.")
                con.execute("UPDATE os_operations SET status=?, ended_at=? WHERE operation_id=?",
                            ("Failed", datetime.now().astimezone().isoformat(timespec="seconds"), operation_id))
            raise

    def list_students(self, search: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            return self.list_students_for(search, self.active_student_id)
        pattern = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute("""SELECT * FROM students
                WHERE student_id LIKE ? OR full_name LIKE ? OR program LIKE ? OR email LIKE ?
                ORDER BY full_name""", (pattern, pattern, pattern, pattern)).fetchall()

    def list_students_for(self, search: str = "", student_id: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return []
        if not student_id:
            return self.list_students(search)
        pattern = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute("""SELECT * FROM students WHERE student_id=? AND
                (student_id LIKE ? OR full_name LIKE ? OR program LIKE ? OR email LIKE ?)
                ORDER BY full_name""", (student_id, pattern, pattern, pattern, pattern)).fetchall()

    def list_courses(self, search: str = "") -> list[sqlite3.Row]:
        pattern = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute("""SELECT * FROM courses WHERE course_code LIKE ? OR course_name LIKE ? OR department LIKE ?
                ORDER BY semester, course_code""", (pattern, pattern, pattern)).fetchall()

    def list_course_choices(self) -> list[tuple[str, str]]:
        with self.connect() as con:
            return [(row["course_code"], row["course_name"]) for row in
                    con.execute("SELECT course_code, course_name FROM courses ORDER BY course_code").fetchall()]

    def save_course(self, data: dict[str, object], original_code: str | None = None) -> None:
        self._require_role("Administrator")
        action = "Update course" if original_code else "Add course"
        details = f"Saved {data['course_code']} — {data['course_name']}"
        def work(con: sqlite3.Connection) -> None:
            if original_code:
                con.execute("""UPDATE courses SET course_code=?, course_name=?, department=?, credits=?, semester=?
                    WHERE course_code=?""", (*data.values(), original_code))
            else:
                con.execute("""INSERT INTO courses (course_code, course_name, department, credits, semester)
                    VALUES (?, ?, ?, ?, ?)""", tuple(data.values()))
        self._run_operation(action, details, work)

    def delete_course(self, course_code: str) -> None:
        self._require_role("Administrator")
        def work(con: sqlite3.Connection) -> None:
            if con.execute("SELECT 1 FROM academic_records WHERE course_code=? LIMIT 1", (course_code,)).fetchone():
                raise ValueError("This course has saved marks. Remove or update those records first.")
            if con.execute("SELECT 1 FROM session_attendance WHERE course_code=? LIMIT 1", (course_code,)).fetchone():
                raise ValueError("This course has attendance history. Keep it in the catalog or remove those entries first.")
            con.execute("DELETE FROM courses WHERE course_code=?", (course_code,))
        self._run_operation("Delete course", f"Deleted course {course_code}", work)

    def get_student(self, student_id: str) -> sqlite3.Row | None:
        if self.active_role == "Student" and student_id != self.active_student_id:
            return None
        with self.connect() as con:
            return con.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()

    def save_student(self, data: dict[str, object], original_id: str | None = None) -> None:
        self._require_role("Administrator")
        if original_id:
            action, details = "Update student", f"Updated student {data['student_id']}"
        else:
            action, details = "Add student", f"Added student {data['student_id']}"

        def work(con: sqlite3.Connection) -> None:
            if original_id:
                con.execute("""UPDATE students SET student_id=?, full_name=?, program=?, semester=?, email=?, phone=?
                    WHERE student_id=?""", (*data.values(), original_id))
            else:
                con.execute("""INSERT INTO students (student_id, full_name, program, semester, email, phone)
                    VALUES (?, ?, ?, ?, ?, ?)""", tuple(data.values()))
        self._run_operation(action, details, work)

    def delete_student(self, student_id: str) -> None:
        self._require_role("Administrator")
        def work(con: sqlite3.Connection) -> None:
            con.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        self._run_operation("Delete student", f"Deleted student {student_id} and linked course records", work)

    def list_records(self, search: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            return self.list_records_for(search, self.active_student_id)
        pattern = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute("""SELECT r.*, s.full_name FROM academic_records r
                JOIN students s ON s.student_id=r.student_id
                WHERE r.student_id LIKE ? OR s.full_name LIKE ? OR r.course_code LIKE ? OR r.course_name LIKE ?
                ORDER BY s.full_name, r.term, r.course_code""", (pattern, pattern, pattern, pattern)).fetchall()

    def list_records_for(self, search: str = "", student_id: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return []
        if not student_id:
            return self.list_records(search)
        pattern = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute("""SELECT r.*, s.full_name FROM academic_records r
                JOIN students s ON s.student_id=r.student_id
                WHERE r.student_id=? AND (r.student_id LIKE ? OR s.full_name LIKE ? OR r.course_code LIKE ? OR r.course_name LIKE ?)
                ORDER BY s.full_name, r.term, r.course_code""",
                (student_id, pattern, pattern, pattern, pattern)).fetchall()

    def save_record(self, data: dict[str, object], record_id: int | None = None) -> None:
        self._require_role("Administrator", "Faculty")
        if record_id is None:
            action, details = "Add course record", f"Saved {data['course_code']} for student {data['student_id']}"
        else:
            action, details = "Update course record", f"Updated course record {record_id}"

        def work(con: sqlite3.Connection) -> None:
            if record_id is None:
                con.execute("""INSERT INTO academic_records
                    (student_id, course_code, course_name, term, attendance, marks) VALUES (?, ?, ?, ?, ?, ?)""",
                    tuple(data.values()))
            else:
                con.execute("""UPDATE academic_records SET student_id=?, course_code=?, course_name=?, term=?, attendance=?, marks=?
                    WHERE record_id=?""", (*data.values(), record_id))
        self._run_operation(action, details, work)

    def delete_record(self, record_id: int) -> None:
        self._require_role("Administrator")
        def work(con: sqlite3.Connection) -> None:
            con.execute("DELETE FROM academic_records WHERE record_id=?", (record_id,))
        self._run_operation("Delete course record", f"Deleted course record {record_id}", work)

    def summary(self, student_id: str = "") -> dict[str, object]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return {"students": 0, "records": 0, "avg_marks": 0, "avg_attendance": 0, "recent": []}
        with self.connect() as con:
            if student_id:
                student_count = con.execute("SELECT COUNT(*) FROM students WHERE student_id=?", (student_id,)).fetchone()[0]
                record_count = con.execute("SELECT COUNT(*) FROM academic_records WHERE student_id=?", (student_id,)).fetchone()[0]
                avg_marks = con.execute("SELECT AVG(marks) FROM academic_records WHERE student_id=?", (student_id,)).fetchone()[0]
                avg_attendance = con.execute("SELECT AVG(attendance) FROM academic_records WHERE student_id=?", (student_id,)).fetchone()[0]
                recent = []
            else:
                student_count = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                record_count = con.execute("SELECT COUNT(*) FROM academic_records").fetchone()[0]
                avg_marks = con.execute("SELECT AVG(marks) FROM academic_records").fetchone()[0]
                avg_attendance = con.execute("SELECT AVG(attendance) FROM academic_records").fetchone()[0]
                recent = con.execute("SELECT happened_at, action, details FROM activity_log ORDER BY activity_id DESC LIMIT 8").fetchall()
        return {"students": student_count, "records": record_count,
                "avg_marks": avg_marks or 0, "avg_attendance": avg_attendance or 0, "recent": recent}

    def course_performance_summary(self, student_id: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return []
        with self.connect() as con:
            return con.execute("""SELECT course_code, course_name, AVG(marks) AS average_marks,
                COUNT(*) AS record_count FROM academic_records WHERE (?='' OR student_id=?)
                GROUP BY course_code, course_name ORDER BY average_marks DESC, course_code""",
                (student_id, student_id)).fetchall()

    def list_student_choices(self) -> list[tuple[str, str]]:
        with self.connect() as con:
            rows = con.execute("SELECT student_id, full_name FROM students ORDER BY full_name").fetchall()
            return [(row["student_id"], row["full_name"]) for row in rows]

    def import_students(self, students: list[tuple[str, str, str, int, str, str]]) -> int:
        """Import a validated student batch as one transaction."""
        self._require_role("Administrator")
        if not students:
            return 0

        def work(con: sqlite3.Connection) -> None:
            con.executemany("""INSERT INTO students
                (student_id, full_name, program, semester, email, phone)
                VALUES (?, ?, ?, ?, ?, ?)""", students)

        self._run_operation("Import students", f"Imported {len(students)} student profiles from CSV", work)
        return len(students)

    def list_registrations(self, search: str = "", student_id: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return []
        pattern = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute("""SELECT r.*, s.full_name, s.program, c.course_name, c.credits
                FROM course_registrations r
                JOIN students s ON s.student_id=r.student_id
                JOIN courses c ON c.course_code=r.course_code
                WHERE (?='' OR r.student_id=?)
                  AND (r.student_id LIKE ? OR s.full_name LIKE ? OR r.course_code LIKE ? OR c.course_name LIKE ?)
                ORDER BY r.created_at DESC, s.full_name, r.course_code""",
                (student_id, student_id, pattern, pattern, pattern, pattern)).fetchall()

    def save_registration(self, data: dict[str, object]) -> None:
        self._require_role("Administrator", "Faculty", "Student")
        if self.active_role == "Student":
            if str(data["student_id"]) != self.active_student_id:
                raise PermissionError("Students can request courses only for their own profile.")
            data["status"] = "Requested"
        status = str(data.get("status", "Requested"))
        if status not in {"Requested", "Registered", "Waitlisted", "Completed", "Withdrawn"}:
            raise ValueError("Choose a valid registration status.")
        row = (str(data["student_id"]), str(data["course_code"]), str(data["term"]), status,
               datetime.now().astimezone().isoformat(timespec="seconds"))
        action = "Request course registration" if status == "Requested" else "Register student in course"

        def work(con: sqlite3.Connection) -> None:
            con.execute("""INSERT INTO course_registrations
                (student_id, course_code, term, status, created_at) VALUES (?, ?, ?, ?, ?)""", row)

        self._run_operation(action, f"{row[0]} — {row[1]} — {row[2]} ({status})", work)

    def update_registration_status(self, registration_id: int, status: str) -> None:
        self._require_role("Administrator", "Faculty")
        if status not in {"Requested", "Registered", "Waitlisted", "Completed", "Withdrawn"}:
            raise ValueError("Choose a valid registration status.")

        def work(con: sqlite3.Connection) -> None:
            con.execute("UPDATE course_registrations SET status=? WHERE registration_id=?", (status, registration_id))

        self._run_operation("Update course registration", f"Updated registration {registration_id} to {status}", work)

    def visible_notices(self) -> list[sqlite3.Row]:
        if self.active_role == "Administrator":
            with self.connect() as con:
                return con.execute("SELECT * FROM campus_notices ORDER BY CASE priority WHEN 'Urgent' THEN 0 WHEN 'Important' THEN 1 ELSE 2 END, notice_id DESC").fetchall()
        audience = "Students" if self.active_role == "Student" else "Faculty" if self.active_role == "Faculty" else "All"
        with self.connect() as con:
            return con.execute("""SELECT * FROM campus_notices
                WHERE audience IN ('All', ?) ORDER BY CASE priority WHEN 'Urgent' THEN 0 WHEN 'Important' THEN 1 ELSE 2 END,
                notice_id DESC""", (audience,)).fetchall()

    def create_notice(self, title: str, body: str, audience: str, priority: str) -> None:
        self._require_role("Administrator")
        if audience not in {"All", "Faculty", "Students"} or priority not in {"Normal", "Important", "Urgent"}:
            raise ValueError("Choose a valid notice audience and priority.")
        created = datetime.now().astimezone().isoformat(timespec="seconds")

        def work(con: sqlite3.Connection) -> None:
            con.execute("""INSERT INTO campus_notices
                (title, body, audience, priority, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)""", (title.strip(), body.strip(), audience, priority, created, self.active_role))

        self._run_operation("Publish campus notice", f"Published '{title.strip()}' for {audience}", work)

    def list_session_attendance(self, course_code: str = "", student_id: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return []
        with self.connect() as con:
            return con.execute("""SELECT a.*, s.full_name, c.course_name FROM session_attendance a
                JOIN students s ON s.student_id=a.student_id JOIN courses c ON c.course_code=a.course_code
                WHERE (?='' OR a.course_code=?) AND (?='' OR a.student_id=?)
                ORDER BY a.session_date DESC, s.full_name""",
                (course_code, course_code, student_id, student_id)).fetchall()

    def save_session_attendance(self, data: dict[str, object], attendance_id: int | None = None) -> None:
        self._require_role("Administrator", "Faculty")
        action = "Update session attendance" if attendance_id else "Mark session attendance"
        details = f"{data['status']} — {data['student_id']} — {data['course_code']} on {data['session_date']}"
        def work(con: sqlite3.Connection) -> None:
            if attendance_id:
                con.execute("""UPDATE session_attendance SET student_id=?, course_code=?, session_date=?, status=?
                    WHERE attendance_id=?""", (*data.values(), attendance_id))
            else:
                con.execute("""INSERT INTO session_attendance (student_id, course_code, session_date, status)
                    VALUES (?, ?, ?, ?)""", tuple(data.values()))
        self._run_operation(action, details, work)

    def delete_session_attendance(self, attendance_id: int) -> None:
        self._require_role("Administrator")
        def work(con: sqlite3.Connection) -> None:
            con.execute("DELETE FROM session_attendance WHERE attendance_id=?", (attendance_id,))
        self._run_operation("Delete session attendance", f"Deleted attendance entry {attendance_id}", work)

    def session_attendance_summary(self, student_id: str = "") -> list[sqlite3.Row]:
        if self.active_role == "Student":
            student_id = self.active_student_id
            if not student_id:
                return []
        with self.connect() as con:
            return con.execute("""SELECT a.student_id, s.full_name, a.course_code, c.course_name,
                COUNT(*) AS total_sessions, SUM(CASE WHEN a.status IN ('Present','Late') THEN 1 ELSE 0 END) AS attended
                FROM session_attendance a JOIN students s ON s.student_id=a.student_id
                JOIN courses c ON c.course_code=a.course_code WHERE (?='' OR a.student_id=?)
                GROUP BY a.student_id, a.course_code ORDER BY s.full_name, a.course_code""",
                (student_id, student_id)).fetchall()

    def recent_operations(self, limit: int = 25) -> list[sqlite3.Row]:
        with self.connect() as con:
            if self.active_role == "Student":
                return []
            if self.active_role == "Faculty":
                return con.execute("SELECT * FROM os_operations WHERE actor_role='Faculty' ORDER BY operation_id DESC LIMIT ?",
                                   (limit,)).fetchall()
            return con.execute("SELECT * FROM os_operations ORDER BY operation_id DESC LIMIT ?", (limit,)).fetchall()

    def operation_events(self, operation_id: int) -> list[sqlite3.Row]:
        with self.connect() as con:
            return con.execute("SELECT * FROM os_operation_events WHERE operation_id=? ORDER BY event_id",
                               (operation_id,)).fetchall()

    def create_backup(self, destination: str | Path) -> Path:
        self._require_role("Administrator")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == self.path.resolve():
            raise ValueError("Choose a different file name for the backup.")

        def work(con: sqlite3.Connection) -> None:
            with self.connect() as source, sqlite3.connect(target) as backup:
                source.backup(backup)
        self._run_operation("Create backup", f"Saved a database backup to {target.name}", work)
        return target

    def export_academic_records(self, destination: str | Path) -> Path:
        self._require_role("Administrator")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        def work(con: sqlite3.Connection) -> None:
            rows = con.execute("""SELECT r.student_id, s.full_name, r.course_code, r.course_name, r.term,
                r.attendance, r.marks FROM academic_records r JOIN students s ON s.student_id=r.student_id
                ORDER BY s.full_name, r.term, r.course_code""").fetchall()
            with target.open("w", newline="", encoding="utf-8-sig") as output:
                writer = csv.writer(output)
                writer.writerow(("Student ID", "Student name", "Course code", "Course name", "Term", "Attendance percent", "Marks percent"))
                for row in rows:
                    writer.writerow(tuple(row))
        self._run_operation("Export course records", f"Exported course records to {target.name}", work)
        return target
