"""Illustrative workload; these are not real student records or measurements."""

from models import Request


# These records are clearly synthetic and are loaded only alongside the starter demo data.
DEMO_STUDENTS = [
    ("OS2504", "Mira Iyer", "B.Tech CSE", 3, "mira.demo@example.edu", "9000000014"),
    ("OS2505", "Rehan Khan", "B.Tech CSE", 3, "rehan.demo@example.edu", "9000000015"),
    ("OS2506", "Anaya Nair", "B.Tech IT", 5, "anaya.demo@example.edu", "9000000016"),
    ("OS2507", "Ishaan Rao", "B.Tech CSE", 5, "ishaan.demo@example.edu", "9000000017"),
    ("OS2508", "Sara Thomas", "BCA", 3, "sara.demo@example.edu", "9000000018"),
    ("OS2509", "Dev Patel", "B.Tech IT", 3, "dev.demo@example.edu", "9000000019"),
    ("OS2510", "Tara Bose", "B.Tech CSE", 5, "tara.demo@example.edu", "9000000020"),
    ("OS2511", "Arjun Das", "BCA", 5, "arjun.demo@example.edu", "9000000021"),
    ("OS2512", "Nisha Kapoor", "B.Tech CSE", 3, "nisha.demo@example.edu", "9000000022"),
    ("OS2513", "Vihaan Shah", "B.Tech IT", 5, "vihaan.demo@example.edu", "9000000023"),
    ("OS2514", "Meera Joshi", "BCA", 3, "meera.demo@example.edu", "9000000024"),
    ("OS2515", "Ayaan Roy", "B.Tech CSE", 5, "ayaan.demo@example.edu", "9000000025"),
]

DEMO_COURSES = [
    ("CCSE0303B", "Data Structures", "Computer Science", 4, 3),
    ("CCSE0303C", "Database Systems", "Computer Science", 4, 3),
    ("CCSE0303D", "Computer Networks", "Computer Science", 3, 3),
    ("CCSE0502A", "Operating Systems II", "Computer Science", 4, 5),
    ("CCIT0501A", "Cloud Computing", "Information Technology", 3, 5),
    ("BCA0302A", "Python Programming", "Computer Applications", 4, 3),
]

DEMO_SESSIONS = ("2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22")


def sample_requests() -> list[Request]:
    return [
        Request("P1", "Admin", "Add student profile", 0, 4, 1),
        Request("P2", "Faculty", "Save course marks", 1, 3, 1),
        Request("P3", "Faculty", "Update attendance", 2, 5, 2),
        Request("P4", "Admin", "Export course records", 3, 2, 0),
        Request("P5", "Admin", "Back up database", 4, 3, 2),
    ]
