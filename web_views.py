"""HTML views for the dependency-free CampusDesk web interface."""

from html import escape
from urllib.parse import quote


def e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def csrf(token: str) -> str:
    return f'<input type="hidden" name="csrf" value="{e(token)}">'


def options(rows, selected="", value_key=None, label_key=None):
    result = []
    for row in rows:
        if value_key:
            value = row[value_key]
            label = row[label_key]
        else:
            value, label = row
        marker = " selected" if str(value) == str(selected) else ""
        result.append(f'<option value="{e(value)}"{marker}>{e(label)}</option>')
    return "".join(result)


def login_page(token, error=""):
    alert = f'<div class="login-error" role="alert">{e(error)}</div>' if error else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#f7f8ff"><title>Sign in · CampusDesk</title><link rel="stylesheet" href="/static/campusdesk.css"><link rel="stylesheet" href="/static/erp-theme.css"></head>
      <body class="login-page"><main class="login-layout"><section class="login-aside"><a class="login-brand" href="/login"><span class="brand-mark">C</span><span>Campus<strong>Desk</strong></span></a><div class="login-promo"><span class="login-kicker">YOUR CAMPUS. ONE PLACE.</span><h1>Make your next<br>move count.</h1><p>Stay on top of classes, results, and everything happening across campus.</p><div class="promo-art" aria-hidden="true"><div class="art-window"><div class="art-top"><i></i><i></i><i></i><span>Campus overview</span></div><div class="art-tiles"><div><small>ACADEMIC PROGRESS</small><strong>On track <b>↗</b></strong><i></i></div><div><small>UP NEXT</small><strong>Operating Systems</strong><span>11:00 · Lab 3</span></div><div class="art-wide"><small>YOUR WEEK, AT A GLANCE</small><div><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></div></div></div><span class="art-orbit orbit-one"></span><span class="art-orbit orbit-two"></span></div></div><div class="login-aside-foot"><span>●</span> A connected campus experience</div></section>
      <section class="login-main"><button class="header-icon theme-toggle login-theme-toggle" type="button" aria-label="Switch to dark theme" title="Switch to dark theme" aria-pressed="false">◐</button><div class="login-card"><div class="login-mobile-brand"><span class="brand-mark">C</span><span>Campus<strong>Desk</strong></span></div><div class="login-heading"><span class="login-kicker">WELCOME TO CAMPUSDESK</span><h2>Sign in to your portal</h2><p>Use your university account to continue.</p></div>{alert}<form method="post" action="/login" class="login-form">{csrf(token)}<div class="login-field"><label for="login-name">University ID or email</label><div class="login-input-wrap"><span aria-hidden="true">＠</span><input id="login-name" name="login_name" type="text" autocomplete="username" placeholder="e.g. OS2501 or name@university.edu" required></div></div><div class="login-field"><div class="login-label-row"><label for="login-password">Password</label><span>Secure sign-in</span></div><div class="login-input-wrap"><span aria-hidden="true">⌑</span><input id="login-password" name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required><button type="button" class="password-toggle" aria-label="Show password" aria-pressed="false">Show</button></div></div><div class="login-options"><span>Protected sign-in</span><span>8-hour session</span></div><button class="login-submit" type="submit">Sign in securely <span>→</span></button></form><div class="login-divider"><span>ROLE BASED ACCESS</span></div><div class="role-pills"><span>Student</span><span>Faculty</span><span>Administrator</span></div><p class="login-help">Your account type is detected automatically when you sign in. Need access? Contact your campus IT help desk.</p><details class="demo-access"><summary>Demo account access</summary><div><p><b>Student</b> · ID <code>OS2501</code> · Password <code>Campus@123</code></p><p><b>Faculty</b> · <code>faculty@campusdesk.edu</code> · <code>Faculty@123</code></p><p><b>Administrator</b> · <code>admin@campusdesk.edu</code> · <code>Admin@123</code></p></div></details></div><footer class="login-footer"><span>© CampusDesk · University Student ERP</span><span>Demo system · Sample data only</span></footer></section></main><script src="/static/campusdesk.js" defer></script></body></html>'''


def shell(title, body, *, role, student_id, students, active, token, display_name="Campus user", notice=""):
    role_links = {
        "Administrator": [
            ("Workspace", [("/", "Overview", "OV"), ("/students", "Students", "ST"), ("/import", "CSV import", "UP"),
                           ("/courses", "Course catalog", "CO"), ("/registration", "Course registration", "EN"),
                           ("/records", "Marks & results", "MR"), ("/attendance", "Attendance", "AT"),
                           ("/reports", "Student reports", "RP")]),
            ("Campus", [("/notices", "Notices", "NT"), ("/os-lab", "OS concepts", "OS")]),
        ],
        "Faculty": [
            ("Teaching", [("/", "Overview", "OV"), ("/students", "Student roster", "ST"),
                          ("/courses", "Course catalog", "CO"), ("/registration", "Course registration", "EN"),
                          ("/records", "Marks & results", "MR"), ("/attendance", "Attendance", "AT"),
                          ("/reports", "Student reports", "RP")]),
            ("Campus", [("/notices", "Notices", "NT"), ("/os-lab", "OS concepts", "OS")],),
        ],
        "Student": [
            ("Your workspace", [("/", "Dashboard", "DB"), ("/records", "Grades & transcript", "GR"),
                           ("/attendance", "Schedule & attendance", "SC"), ("/fees", "Tuition & fees", "FE")]),
            ("Campus", [("/notices", "Campus life", "CL"), ("/registration", "Course registration", "EN"), ("/reports", "Profile & ID card", "ID")]),
        ],
    }
    sections = role_links.get(role, role_links["Administrator"])
    nav = []
    for section in sections:
        heading, links = section[0], section[1]
        nav.append(f'<div class="nav-label">{e(heading)}</div>')
        for href, label, glyph in links:
            selected = " active" if active == href else ""
            current = ' aria-current="page"' if active == href else ""
            nav.append(f'<a class="nav-link{selected}" href="{href}" aria-label="{e(label)}" title="{e(label)}"{current}><span class="nav-glyph" aria-hidden="true">{e(glyph)}</span><span>{e(label)}</span></a>')
    flash = f'<div class="flash" role="status" aria-live="polite">{e(notice)}</div>' if notice else ""
    demo_label = '<span class="demo-chip">SIGNED IN</span>'
    logout = f'<form method="post" action="/logout" class="logout-form">{csrf(token)}<button type="submit" aria-label="Sign out" title="Sign out">↗</button></form>'
    if role == "Student":
        role_control = f'<div class="header-tools"><label class="top-select semester-select">Semester<select aria-label="Active semester"><option>Semester 3 · 2026</option><option>Semester 2 · 2026</option></select></label><a class="header-icon" href="/notices" aria-label="Notifications" title="Campus notifications">♢<i></i></a><button class="header-icon theme-toggle" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">◐</button><a class="profile-shortcut" href="/reports" aria-label="Open student ID card">{e((student_id or "S")[:2])}<span>My ID</span></a>{logout}</div>'
    else:
        role_control = f'<div class="header-tools"><div class="signed-in-user"><span class="user-avatar">{e(display_name[:1].upper())}</span><span><strong>{e(display_name)}</strong><small>{e(role)}</small></span></div><button class="header-icon theme-toggle" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">◐</button>{logout}</div>'
    mobile_items = [("/", "Home", "⌂"), ("/attendance", "Schedule", "◷"), ("/records", "Grades", "▤"), ("/fees", "Fees", "＄")]
    mobile_links = []
    for href, label, glyph in mobile_items:
        is_active = active == href
        current = ' aria-current="page"' if is_active else ""
        active_class = "active" if is_active else ""
        mobile_links.append(f'<a href="{href}" class="{active_class}" aria-label="{label}"{current}><span aria-hidden="true">{glyph}</span><small>{label}</small></a>')
    mobile_nav = ''.join(mobile_links) if role == "Student" else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
      <meta name="theme-color" content="#f7f8ff"><title>{e(title)} · CampusDesk</title><link rel="stylesheet" href="/static/campusdesk.css"><link rel="stylesheet" href="/static/erp-theme.css"></head>
      <body class="{"student-portal" if role == "Student" else ""}"><div class="app-shell"><aside class="sidebar"><a class="brand" href="/"><span class="brand-mark">C</span><span>Campus<span class="brand-light">Desk</span><small>STUDENT PORTAL</small></span></a>
      <div class="side-role">{demo_label}<span>{e(role)} workspace</span></div><nav id="campus-navigation" aria-label="Main navigation">{''.join(nav)}</nav>
      <div class="sidebar-foot"><div class="online-mark"></div><div><strong>Signed in securely</strong><small>{e(display_name)}</small></div></div></aside>
      <main class="main-area"><header class="topbar"><button class="mobile-menu-toggle" type="button" aria-label="Open navigation menu" aria-controls="campus-navigation" aria-expanded="false">☰</button><div class="mobile-brand">Campus<span>Desk</span></div><div class="topbar-note"><span class="status-dot"></span>{"Your campus, all in one place" if role == "Student" else "Campus administration workspace"}</div>{role_control}</header><div class="content">{f'<div class="page-heading"><div><div class="eyebrow">CAMPUSDESK / {e(role.upper())}</div><h1>{e(title)}</h1></div></div>' if role != "Student" else ''}{flash}{body}
      <footer class="page-foot">CampusDesk academic prototype <span>·</span> Data is stored locally in SQLite</footer></div></main>{f'<nav class="mobile-bottom-nav" aria-label="Student navigation">{mobile_nav}</nav>' if mobile_nav else ''}<button class="nav-backdrop" type="button" aria-label="Close navigation menu" tabindex="-1"></button></div><script src="/static/campusdesk.js" defer></script></body></html>'''


def stat_card(label, value, note, glyph, tone="blue"):
    return f'''<article class="stat-card"><div class="stat-icon {e(tone)}">{e(glyph)}</div><div class="stat-label">{e(label)}</div>
      <div class="stat-value">{e(value)}</div><div class="stat-note">{e(note)}</div></article>'''


def data_table(headers, rows, empty="No records to show yet.", class_name=""):
    if not rows:
        return f'<div class="empty-state">{e(empty)}</div>'
    head = "".join(f"<th>{e(label)}</th>" for label in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table class="data-table {e(class_name)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def badge(value):
    safe = e(value)
    cls = str(value).lower().replace(" ", "-")
    return f'<span class="badge {e(cls)}">{safe}</span>'


def dashboard_page(role, summary, course_rows, attendance_rows, notices, recent, student=None):
    is_student = role == "Student"
    if is_student:
        return student_dashboard_page(summary, course_rows, attendance_rows, notices, student)
    greeting = f"Welcome back, {student['full_name'].split()[0]}" if is_student and student else f"Good day, {role}"
    subtitle = "Here is your academic progress at a glance." if is_student else "Your campus records and activity in one place."
    tiles = [
        stat_card("Students", summary["students"], "Active student profiles", "ST", "blue"),
        stat_card("Course records", summary["records"], "Marks and term results", "MR", "violet"),
        stat_card("Average marks", f"{summary['avg_marks']:.1f}%", "Across saved records", "↗", "green"),
        stat_card("Attendance", f"{summary['avg_attendance']:.1f}%", "Session attendance average", "AT", "amber"),
    ]
    if is_student:
        tiles[0] = stat_card("My profile", student["student_id"] if student else "—", student["program"] if student else "Choose a profile", "ST", "blue")
    bars = []
    max_value = max([float(r["average_marks"] or 0) for r in course_rows] or [100])
    for row in course_rows[:6]:
        value = float(row["average_marks"] or 0)
        width = max(6, round(value))
        bars.append(f'''<div class="bar-row"><div class="bar-name"><strong>{e(row['course_code'])}</strong><span>{e(row['course_name'])}</span></div>
          <div class="bar-track"><i style="width:{width}%"></i></div><b>{value:.0f}%</b></div>''')
    if not bars:
        bars.append('<div class="empty-state compact">Marks will appear after course records are added.</div>')
    low = []
    for row in attendance_rows:
        total = int(row["total_sessions"] or 0)
        rate = 100 * int(row["attended"] or 0) / total if total else 0
        if total and rate < 75:
            low.append(f'<div class="alert-line"><span>{e(row["course_code"])}</span><strong>{rate:.0f}%</strong></div>')
    if low:
        alert_body = f'<div class="alert-banner"><span class="alert-symbol">!</span><div><strong>{len(low)} attendance warning(s)</strong><p>These course rates are below 75%.</p></div></div>{"".join(low[:4])}'
    else:
        alert_body = '<div class="success-banner"><span>✓</span><div><strong>Attendance looks good</strong><p>No course is currently below 75%.</p></div></div>'
    recent_rows = [[e(r["happened_at"])[:16].replace("T", " "), e(r["action"]), e(r["details"])] for r in recent[:6]]
    notice_rows = notices[:3]
    notice_html = "".join(f'<div class="notice-mini"><span class="notice-priority {e(n["priority"].lower())}"></span><div><strong>{e(n["title"])}</strong><small>{e(n["audience"])} · {e(n["created_at"])[:10]}</small></div></div>' for n in notice_rows)
    return f'''<section class="welcome-row"><div><p class="welcome-kicker">CAMPUS OVERVIEW</p><h2>{e(greeting)}</h2><p>{e(subtitle)}</p></div><a class="button primary" href="/reports">View student report <span>→</span></a></section>
      <section class="stats-grid">{''.join(tiles)}</section><section class="dashboard-grid"><article class="panel chart-panel"><div class="panel-heading"><div><h3>Course performance</h3><p>Average marks by course</p></div><a href="/records">All results ↗</a></div><div class="bars">{''.join(bars)}</div></article>
      <article class="panel"><div class="panel-heading"><div><h3>Attendance monitor</h3><p>Early warning at 75%</p></div><a href="/attendance">View attendance ↗</a></div>{alert_body}</article>
      <article class="panel activity-panel"><div class="panel-heading"><div><h3>Recent activity</h3><p>Actions saved in the SIS</p></div><a href="/os-lab">OS traces ↗</a></div>{data_table(["Time", "Action", "Details"], recent_rows, "Your recent activity will appear here.", "small-table")}</article>
      <article class="panel notice-panel"><div class="panel-heading"><div><h3>Campus notices</h3><p>Updates for your workspace</p></div><a href="/notices">All notices ↗</a></div>{notice_html or '<div class="empty-state compact">No notices published.</div>'}</article></section>'''


def student_dashboard_page(summary, course_rows, attendance_rows, notices, student):
    from datetime import date, timedelta
    name = student["full_name"] if student else "Student"
    first = name.split()[0]
    scores = [float(row["average_marks"] or 0) for row in course_rows]
    average = sum(scores) / len(scores) if scores else 0
    gpa = min(10, average / 10)
    ring = round(gpa / 10 * 100)
    course_names = [row["course_name"] for row in course_rows[:3]] or ["Operating Systems", "Database Systems", "Data Structures"]
    today = date.today()
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = weekdays[today.weekday()]
    sessions = [
        ("09:00", course_names[0], "Dr. Ananya Rao", "Block A · 204"),
        ("11:00", course_names[1 % len(course_names)], "Prof. Karan Mehta", "Lab 3 · Block C"),
        ("14:00", course_names[2 % len(course_names)], "Dr. Mira Sen", "Block B · 108"),
    ] if today.weekday() < 5 else []
    from datetime import datetime
    current_hour = datetime.now().hour
    class_cards = []
    for time, course, professor, room in sessions:
        hour = int(time.split(":")[0])
        live = hour <= current_hour < hour + 1
        status_html = '<span class="live-pill"><i></i> Live</span>' if live else '<span class="class-arrow">›</span>'
        class_cards.append(f'<div class="class-row"><div class="class-time">{time}<small>{"NOW" if live else "AM" if hour < 12 else "PM"}</small></div><div class="class-mark">{e(course[:1])}</div><div class="class-info"><strong>{e(course)}</strong><span>{e(professor)} · {e(room)}</span></div>{status_html}</div>')
    schedule_status = "Happening now" if any("class=" in card and "live-pill" in card for card in class_cards) else "Today's schedule"
    if not class_cards:
        class_cards.append('<div class="empty-state compact">No classes today. Enjoy the break!</div>')
    deadlines = [(1, "Operating Systems", "Assignment 4", "Assignment"), (3, "Data Structures", "Quiz 2", "Quiz"), (6, "Database Systems", "Project checkpoint", "Project")]
    deadline_cards = []
    for offset, course, title, kind in deadlines:
        due = today + timedelta(days=offset)
        label = "Tomorrow" if offset == 1 else due.strftime("%a, %d %b")
        deadline_cards.append(f'<div class="deadline-row"><span class="deadline-date">{due.strftime("%d")}<small>{due.strftime("%b")}</small></span><span class="deadline-copy"><strong>{e(title)}</strong><small>{e(course)} · {e(kind)}</small></span><span class="deadline-state {"due-today" if offset == 0 else "due-soon"}">{label}</span></div>')
    total_fees = 48500
    paid_fees = 36000
    outstanding = total_fees - paid_fees
    due_rows = ''.join(f'<div class="grade-mini"><span>{e(row["course_code"])}</span><strong>{float(row["average_marks"] or 0):.0f}<small>%</small></strong><b>{"A" if float(row["average_marks"] or 0)>=85 else "B+" if float(row["average_marks"] or 0)>=75 else "B"}</b></div>' for row in course_rows[:3])
    attendance_avg = float(summary["avg_attendance"] or 0)
    notice = notices[0] if notices else None
    notice_html = f'<a class="notice-strip" href="/notices"><span class="notice-strip-icon">✦</span><span><strong>{e(notice["title"])}</strong><small>{e(notice["body"])[:100]}</small></span><b>›</b></a>' if notice else ''
    return f'''<section class="student-welcome"><div><div class="eyebrow">{today.strftime("%A, %d %B %Y").upper()} <span class="sample-label">SAMPLE CAMPUS SCHEDULE</span></div><h1>Hey {e(first)} <span class="wave">✦</span></h1><p>Here’s what’s happening with your campus life today.</p></div><a class="student-id-pill" href="/reports"><span class="student-avatar">{e(first[:1].upper())}</span><span><strong>{e(name)}</strong><small>{e(student["student_id"] if student else "Student ID")} · {e(student["program"] if student else "University")}</small></span><b>›</b></a></section>
      <section class="student-bento"><article class="student-card schedule-card"><div class="student-card-head"><div><span class="card-eyebrow">YOUR DAY · {day_name.upper()}</span><h2>Today’s classes</h2></div><a href="/attendance" class="card-link">Full schedule ↗</a></div><div class="class-list">{''.join(class_cards)}</div><div class="schedule-footer"><span class="live-legend">{('<i></i> ' if schedule_status == "Happening now" else '')}{schedule_status}</span><span>All times local · Sample schedule</span></div></article>
      <article class="student-card gpa-card"><div class="student-card-head"><div><span class="card-eyebrow">ACADEMIC PROGRESS</span><h2>Your GPA</h2></div><a href="/reports" aria-label="Open transcript" class="circle-link">↗</a></div><div class="gpa-content"><div class="gpa-ring" role="img" aria-label="Estimated GPA {gpa:.1f} out of 10"><svg viewBox="0 0 100 100" aria-hidden="true"><circle class="gpa-track" cx="50" cy="50" r="43"></circle><circle class="gpa-value" cx="50" cy="50" r="43" style="stroke-dasharray:{ring*2.7018:.1f} 270.18"></circle></svg><div><strong>{gpa:.1f}</strong><small>/ 10</small></div></div><div><span class="gpa-trend">↗ On track</span><p>Based on your<br>recorded marks</p></div></div><div class="gpa-bottom"><span>Estimated cumulative GPA</span><a href="/reports">View transcript →</a></div></article>
      <article class="student-card deadline-card"><div class="student-card-head"><div><span class="card-eyebrow">KEEP IT MOVING</span><h2>Coming up</h2></div><span class="week-chip">Next 7 days</span></div><div class="deadline-list">{''.join(deadline_cards)}</div><a class="all-deadlines" href="/records">See all coursework <span>→</span></a><p class="sample-note">Sample deadlines · Not linked to faculty assignment records yet</p></article>
      <article class="student-card finance-card"><div class="finance-top"><span class="card-eyebrow">TUITION & FEES <span class="sample-label">DEMO</span></span><span class="shield">✓</span></div><h2>One step closer<br>to fee clearance.</h2><p>Current semester balance</p><div class="fee-amount">₹{outstanding:,}<small>.00</small></div><div class="fee-progress"><span style="width:{round(paid_fees/total_fees*100)}%"></span></div><div class="fee-meta"><span>₹{paid_fees:,} paid</span><span>₹{total_fees:,} total</span></div><button type="button" class="pay-button" disabled aria-describedby="pay-note">Pay fees <span>→</span></button><small class="pay-note" id="pay-note">Payments are not connected in this demo.</small></article>
      <article class="student-card grades-card"><div class="student-card-head"><div><span class="card-eyebrow">LATEST RESULTS</span><h2>Course snapshot</h2></div><a href="/records" class="card-link">All grades ↗</a></div><div class="grade-list">{due_rows or '<div class="empty-state compact">Your results will appear here.</div>'}</div><div class="attendance-mini"><span>Overall attendance</span><strong>{attendance_avg:.0f}%</strong><div class="attendance-meter"><i style="width:{max(0,min(100,attendance_avg))}%"></i></div></div></article>
      <article class="student-card campus-card"><div class="student-card-head"><div><span class="card-eyebrow">CAMPUS PULSE</span><h2>Stay in the loop</h2></div><a class="circle-link" href="/notices" aria-label="Open campus notices">↗</a></div>{notice_html or '<p class="campus-empty">Your campus announcements and student updates will show here.</p>'}<div class="campus-links"><a href="/notices">Campus notices <span>↗</span></a><a href="/registration">My courses <span>↗</span></a></div></article></section>'''


def fees_page(student):
    sid = student["student_id"] if student else "Student profile"
    name = student["full_name"] if student else "Student"
    return f'''<section class="student-welcome fees-welcome"><div><div class="eyebrow">STUDENT FINANCIALS <span class="sample-label">DEMO DATA</span></div><h1>Tuition & fees</h1><p>Review your semester charges and payment history.</p></div><a class="student-id-pill" href="/reports"><span class="student-avatar">{e(name[:1].upper())}</span><span><strong>{e(name)}</strong><small>{e(sid)}</small></span><b>›</b></a></section>
      <section class="fees-layout"><article class="student-card finance-card fees-primary"><div class="finance-top"><span class="card-eyebrow">SEMESTER 3 · 2026 <span class="sample-label">SAMPLE</span></span><span class="shield">✓</span></div><h2>Current balance</h2><p>Sample tuition and campus charges</p><div class="fee-amount">₹12,500<small>.00</small></div><div class="fee-progress"><span style="width:74%"></span></div><div class="fee-meta"><span>₹36,000 paid</span><span>₹48,500 total</span></div><button type="button" class="pay-button" data-payment-open aria-describedby="pay-note">Pay fees <span>→</span></button><small class="pay-note" id="pay-note">Prototype checkout · no real payment will be made.</small></article><article class="student-card fee-breakdown"><div class="student-card-head"><div><span class="card-eyebrow">CHARGES</span><h2>Fee breakdown</h2></div></div><div class="fee-line"><span>Tuition fee</span><strong>₹32,000</strong><small>Paid</small></div><div class="fee-line"><span>Laboratory fee</span><strong>₹6,000</strong><small>Paid</small></div><div class="fee-line"><span>Library & campus</span><strong>₹4,000</strong><small>Paid</small></div><div class="fee-line due"><span>Semester balance</span><strong>₹12,500</strong><small>Due · sample</small></div></article></section><p class="fees-footnote">This screen uses illustrative sample amounts. It is not a bill, payment request, or financial record.</p>
      <dialog class="payment-dialog" aria-labelledby="payment-title"><form method="dialog" class="payment-modal"><button class="payment-close" aria-label="Close payment window">×</button><span class="card-eyebrow">SAMPLE CHECKOUT · NO REAL CHARGE</span><h2 id="payment-title">Pay semester fees</h2><p class="payment-intro">Choose a sample payment method for the outstanding balance.</p><div class="payment-total"><span>Amount due</span><strong>₹12,500.00</strong></div><fieldset class="payment-methods"><legend>Payment method</legend><label><input type="radio" name="payment-method" value="upi" checked><span><b>UPI</b><small>Google Pay, PhonePe, BHIM</small></span></label><label><input type="radio" name="payment-method" value="card"><span><b>Debit or credit card</b><small>Visa, Mastercard, RuPay</small></span></label><label><input type="radio" name="payment-method" value="netbanking"><span><b>Net banking</b><small>Select your bank at the next step</small></span></label></fieldset><div class="payment-demo-notice">Demo only. This prototype does not collect card or bank details and cannot process payments.</div><button type="button" class="button primary payment-confirm" data-payment-confirm>Continue to demo confirmation <span>→</span></button><button type="button" class="payment-cancel" data-payment-close>Cancel</button><div class="payment-success" role="status" hidden>Demo checkout complete. No money was charged.</div></form></dialog>'''


def students_page(rows, role, query, token, editing=None):
    can_manage = role == "Administrator"
    if editing and can_manage:
        form_values = editing
        form_title, button = "Edit student profile", "Save changes"
        original = (f'<input type="hidden" name="original_id" value="{e(editing["student_id"])}">'
                    f'<input type="hidden" name="student_id" value="{e(editing["student_id"])}">')
    else:
        form_values = {"student_id": "", "full_name": "", "program": "", "semester": 1, "email": "", "phone": ""}
        form_title, button, original = "Add student profile", "Add student", ""
    form = ""
    if can_manage:
        form = f'''<details class="panel form-panel" {"open" if editing else ""}><summary><span class="summary-title">＋ {e(form_title)}</span><span class="summary-help">Student ID, course links, and email are checked when you save.</span></summary>
          <form method="post" action="/students/save" class="form-grid">{csrf(token)}{original}
          {input_field("student_id", "Student ID", form_values["student_id"], required=True, disabled=bool(editing))}
          {input_field("full_name", "Full name", form_values["full_name"], required=True)}
          {input_field("program", "Program", form_values["program"], required=True)}
          {input_field("semester", "Current semester", form_values["semester"], kind="number", required=True, extra='min="1" max="12"')}
          {input_field("email", "College email", form_values["email"], kind="email", required=True)}
          {input_field("phone", "Phone (optional)", form_values["phone"])}
          <div class="form-actions"><button class="button primary" type="submit">{button}</button>{"<a class='button quiet' href='/students'>Cancel</a>" if editing else ""}</div></form></details>'''
    rows_html = []
    for r in rows:
        actions = f'<a class="text-action" href="/students?edit={quote(str(r["student_id"]))}">Edit</a><form method="post" action="/students/delete" class="inline-form" data-confirm="Delete this student and linked records?">{csrf(token)}<input type="hidden" name="student_id" value="{e(r["student_id"])}"><button class="text-action danger" type="submit">Delete</button></form>' if can_manage else f'<a class="text-action" href="/reports/{quote(str(r["student_id"]))}">View report</a>'
        rows_html.append([f'<div class="person-cell"><span class="avatar">{e(str(r["full_name"])[:1].upper())}</span><div><strong>{e(r["full_name"])}</strong><small>{e(r["email"])}</small></div></div>', f'<span class="mono">{e(r["student_id"])}</span>', e(r["program"]), f'<span class="semester-pill">Sem {e(r["semester"])}</span>', actions])
    searchbar = f'<form class="search-form" method="get" action="/students"><span>⌕</span><input name="q" value="{e(query)}" placeholder="Search name, ID, program, or email"><button class="button secondary">Search</button></form>'
    return f'''<section class="page-toolbar"><p>{"Manage the student directory and linked academic profiles." if can_manage else "Browse the student roster and open an academic report."}</p>{searchbar}</section>{form}
      <section class="panel table-panel"><div class="panel-heading"><div><h3>Student directory</h3><p>{len(rows)} profile(s) shown</p></div></div>{data_table(["Student", "Student ID", "Program", "Semester", "Actions"], rows_html, "No students match your search.")}</section>'''


def courses_page(rows, role, query, token):
    can_manage = role == "Administrator"
    form = f'''<details class="panel form-panel"><summary><span class="summary-title">＋ Add course</span><span class="summary-help">Add courses to the catalog used by marks, attendance, and registration.</span></summary>
      <form method="post" action="/courses/save" class="form-grid">{csrf(token)}{input_field("course_code", "Course code", required=True)}{input_field("course_name", "Course name", required=True)}
      {input_field("department", "Department", required=True)}{input_field("credits", "Credits", kind="number", required=True, extra='min="1" max="10"')}{input_field("semester", "Semester", kind="number", required=True, extra='min="1" max="12"')}
      <div class="form-actions"><button class="button primary">Add course</button></div></form></details>''' if can_manage else ""
    result = []
    for r in rows:
        result.append([f'<span class="mono">{e(r["course_code"])}</span>', f'<strong>{e(r["course_name"])}</strong>', e(r["department"]), e(r["credits"]), f'<span class="semester-pill">Semester {e(r["semester"])}</span>'])
    search = f'<form class="search-form" method="get"><span>⌕</span><input name="q" value="{e(query)}" placeholder="Search by course, code, or department"><button class="button secondary">Search</button></form>'
    return f'''<section class="page-toolbar"><p>One shared course catalog keeps academic records consistent across the ERP.</p>{search}</section>{form}<section class="panel table-panel"><div class="panel-heading"><div><h3>Course catalog</h3><p>{len(rows)} course(s)</p></div></div>{data_table(["Course code", "Course", "Department", "Credits", "Semester"], result, "No courses match your search.")}</section>'''


def records_page(rows, role, query, students, courses, token):
    can_edit = role in {"Administrator", "Faculty"}
    form = f'''<details class="panel form-panel"><summary><span class="summary-title">＋ Enter course results</span><span class="summary-help">Choose a student and catalog course, then enter term marks.</span></summary>
      <form method="post" action="/records/save" class="form-grid">{csrf(token)}{select_field("student_id", "Student", [(s["student_id"], f'{s["student_id"]} · {s["full_name"]}') for s in students])}
      {select_field("course_code", "Course", [(c["course_code"], f'{c["course_code"]} · {c["course_name"]}') for c in courses])}{input_field("term", "Term", placeholder="Semester 3 · 2026")}
      {input_field("marks", "Marks (%)", kind="number", extra='min="0" max="100" step="0.1"')}{input_field("attendance", "Term attendance (%)", kind="number", extra='min="0" max="100" step="0.1"')}
      <div class="form-actions"><button class="button primary">Save results</button></div></form></details>''' if can_edit else ""
    result = []
    for r in rows:
        status = "Pass" if float(r["marks"]) >= 40 else "Needs review"
        result.append([f'<div class="person-cell"><span class="avatar small-avatar">{e(str(r["full_name"])[:1].upper())}</span><div><strong>{e(r["full_name"])}</strong><small>{e(r["student_id"])}</small></div></div>', f'<strong>{e(r["course_name"])}</strong><small class="sub-cell">{e(r["course_code"])}</small>', e(r["term"]), f'<strong>{float(r["marks"]):.1f}%</strong>', f'{float(r["attendance"]):.1f}%', badge(status)])
    search = f'<form class="search-form" method="get"><span>⌕</span><input name="q" value="{e(query)}" placeholder="Find a student or course"><button class="button secondary">Search</button></form>'
    extra_action = ('<a class="button secondary" href="/export.csv">Download CSV</a>'
                    '<a class="button secondary" href="/backup.db">Backup database</a>') if role == "Administrator" else '<a class="button secondary" href="/reports">Printable report</a>'
    return f'''<section class="page-toolbar"><p>{"Record marks and term attendance against catalog courses." if can_edit else "Review your course results and term attendance."}</p>{search}</section>{form}<section class="panel table-panel"><div class="panel-heading"><div><h3>{"Academic records" if role != "Student" else "My results"}</h3><p>{len(rows)} result record(s)</p></div><div class="action-row">{extra_action}<a class="button secondary" href="/reports">Print report</a></div></div>{data_table(["Student", "Course", "Term", "Marks", "Attendance", "Result"], result, "No academic records have been added yet.")}</section>'''


def attendance_page(rows, summaries, role, students, courses, token):
    can_mark = role in {"Administrator", "Faculty"}
    form = f'''<details class="panel form-panel" open><summary><span class="summary-title">＋ Record a class session</span><span class="summary-help">Late counts as attended. Absent and excused sessions do not.</span></summary>
      <form method="post" action="/attendance/save" class="form-grid">{csrf(token)}{select_field("student_id", "Student", [(s["student_id"], f'{s["student_id"]} · {s["full_name"]}') for s in students])}
      {select_field("course_code", "Course", [(c["course_code"], f'{c["course_code"]} · {c["course_name"]}') for c in courses])}{input_field("session_date", "Class date", kind="date", required=True)}
      {select_field("status", "Attendance", [(s, s) for s in ("Present", "Absent", "Late", "Excused")])}<div class="form-actions"><button class="button primary">Save attendance</button></div></form></details>''' if can_mark else ""
    rows_html = [[e(r["session_date"]), f'<div class="person-cell"><span class="avatar small-avatar">{e(str(r["full_name"])[:1].upper())}</span><div><strong>{e(r["full_name"])}</strong><small>{e(r["student_id"])}</small></div></div>', f'<strong>{e(r["course_code"])}</strong><small class="sub-cell">{e(r["course_name"])}</small>', badge(r["status"])] for r in rows]
    summary_rows = []
    for r in summaries:
        total, attended = int(r["total_sessions"] or 0), int(r["attended"] or 0)
        rate = 100 * attended / total if total else 0
        mark = badge("Below 75%" if rate < 75 else "On track")
        summary_rows.append([e(r["full_name"]), e(r["course_code"]), f"{attended} / {total}", f"{rate:.1f}%", mark])
    return f'''<section class="page-toolbar"><p>Take attendance by class session and spot low attendance before it affects course eligibility.</p></section>{form}
      <section class="panel table-panel"><div class="panel-heading"><div><h3>Attendance by course</h3><p>Course totals use Present and Late as attended.</p></div></div>{data_table(["Student", "Course", "Sessions", "Rate", "Alert"], summary_rows, "Session summaries will appear here.")}</section>
      <section class="panel table-panel"><div class="panel-heading"><div><h3>Recent class sessions</h3><p>Latest attendance entries</p></div></div>{data_table(["Date", "Student", "Course", "Status"], rows_html, "No class sessions recorded.")}</section>'''


def registration_page(rows, role, students, courses, token, selected_student=""):
    can_manage = role in {"Administrator", "Faculty"}
    if role == "Student":
        student_input = f'<input type="hidden" name="student_id" value="{e(selected_student)}"><div class="field"><label>Student profile</label><div class="read-only-value">{e(selected_student)}</div></div>'
        initial = "Requested"
    else:
        student_input = select_field("student_id", "Student", [(s["student_id"], f'{s["student_id"]} · {s["full_name"]}') for s in students])
        initial = "Registered"
    form = f'''<details class="panel form-panel" open><summary><span class="summary-title">＋ {"Request a course" if role == "Student" else "Register a student"}</span><span class="summary-help">Prevent duplicate course requests for the same term.</span></summary>
      <form method="post" action="/registration/save" class="form-grid">{csrf(token)}{student_input}{select_field("course_code", "Course", [(c["course_code"], f'{c["course_code"]} · {c["course_name"]}') for c in courses])}{input_field("term", "Term", placeholder="Semester 3 · 2026", required=True)}
      {f'<input type="hidden" name="status" value="{initial}">' if role == "Student" else select_field("status", "Status", [(s, s) for s in ("Registered", "Waitlisted", "Requested")])}<div class="form-actions"><button class="button primary">{"Send request" if role == "Student" else "Save registration"}</button></div></form></details>'''
    rows_html = []
    for r in rows:
        status_cell = badge(r["status"])
        if can_manage:
            status_cell += f'''<form method="post" action="/registration/status" class="inline-status">{csrf(token)}<input type="hidden" name="registration_id" value="{e(r['registration_id'])}">
                <select name="status" aria-label="Change registration status">{''.join(f'<option{" selected" if s == r["status"] else ""}>{s}</option>' for s in ("Requested", "Registered", "Waitlisted", "Completed", "Withdrawn"))}</select><button class="text-action">Update</button></form>'''
        rows_html.append([e(r["student_id"]), f'<strong>{e(r["full_name"])}</strong><small class="sub-cell">{e(r["program"])}</small>', f'<strong>{e(r["course_code"])}</strong><small class="sub-cell">{e(r["course_name"])}</small>', e(r["term"]), status_cell])
    return f'''<section class="page-toolbar"><p>Track requests, approved course registrations, waitlists, and completed enrollments by term.</p></section>{form}
      <section class="panel table-panel"><div class="panel-heading"><div><h3>Course registrations</h3><p>{len(rows)} registration(s)</p></div></div>{data_table(["Student ID", "Student", "Course", "Term", "Status"], rows_html, "No registrations are listed for this view.")}</section>'''


def notices_page(rows, role, token):
    form = f'''<details class="panel form-panel"><summary><span class="summary-title">＋ Publish a notice</span><span class="summary-help">Share a campus update with students, faculty, or everyone.</span></summary>
      <form method="post" action="/notices/save" class="form-grid">{csrf(token)}{input_field("title", "Notice title", required=True)}{select_field("audience", "Audience", [(a, a) for a in ("All", "Students", "Faculty")])}
      {select_field("priority", "Priority", [(p, p) for p in ("Normal", "Important", "Urgent")])}<div class="field full-field"><label for="body">Message</label><textarea id="body" name="body" rows="3" required></textarea></div><div class="form-actions"><button class="button primary">Publish notice</button></div></form></details>''' if role == "Administrator" else ""
    cards = []
    for n in rows:
        cards.append(f'''<article class="notice-card"><div class="notice-card-top"><span class="notice-priority {e(n['priority'].lower())}"></span>{badge(n['priority'])}<span class="notice-audience">{e(n['audience'])}</span></div>
          <h3>{e(n['title'])}</h3><p>{e(n['body'])}</p><small>Posted by {e(n['created_by'])} · {e(n['created_at'])[:10]}</small></article>''')
    return f'''<section class="page-toolbar"><p>Campus announcements are shown to the audience selected by the administrator.</p></section>{form}<section class="notice-grid">{''.join(cards) or '<div class="empty-state">No notices are available for this workspace.</div>'}</section>'''


def import_page(token):
    return f'''<section class="page-toolbar"><p>Add a whole student group from a CSV file. The import is saved as one database transaction.</p></section>
      <section class="panel import-panel"><div class="import-intro"><div class="stat-icon blue">CSV</div><div><h3>Import student profiles</h3><p>Use the columns below. Student ID and email must be unique.</p></div></div>
      <form method="post" action="/import" enctype="application/x-www-form-urlencoded">{csrf(token)}<label class="file-drop" for="csv-file"><span class="file-icon">↑</span><span><strong>Choose a CSV file</strong><small>It will be read in this browser and submitted to the local app.</small></span><input type="file" id="csv-file" accept=".csv,text/csv"></label>
      <div class="field full-field"><label for="csv-data">CSV data</label><textarea id="csv-data" name="csv_data" rows="9" spellcheck="false" placeholder="student_id,full_name,program,semester,email,phone&#10;STU26001,Sample Student,BTech CSE,1,sample@student.example.edu," required></textarea></div>
      <div class="csv-help"><strong>Required headings:</strong> <code>student_id, full_name, program, semester, email</code><span>Optional: <code>phone</code></span><span>Semester must be 1–12. Example values are placeholders only.</span></div>
      <button class="button primary" type="submit">Import students</button></form></section>'''


def reports_page(role, students, selected_id=""):
    if role == "Student":
        if not selected_id:
            return '<div class="empty-state">Select your demo profile from the top bar to view your report.</div>'
        return f'''<section class="panel report-launch"><div><span class="eyebrow">PRINTABLE STUDENT REPORT</span><h3>Your course results</h3><p>Open a clean transcript-style summary and use your browser’s Print or Save as PDF option.</p></div><a class="button primary" href="/reports/{quote(selected_id)}">Open my report ↗</a></section>'''
    options_html = options([(s["student_id"], f'{s["student_id"]} · {s["full_name"]}') for s in students], selected_id)
    return f'''<section class="page-toolbar"><p>Create a print-ready summary of one student’s course results and session attendance.</p></section>
      <section class="panel report-launch"><div><span class="eyebrow">STUDENT SERVICES</span><h3>Course-results report</h3><p>Choose a student to view their course marks and attendance summary.</p></div><form class="report-picker" method="get"><select name="student_id">{options_html}</select><button class="button primary">Open report ↗</button></form></section>'''


def transcript_page(student, records, summaries):
    rows = [[e(r["term"]), e(r["course_code"]), e(r["course_name"]), f'{float(r["marks"]):.1f}%', f'{float(r["attendance"]):.1f}%'] for r in records]
    total_sessions = sum(int(r["total_sessions"] or 0) for r in summaries)
    attended = sum(int(r["attended"] or 0) for r in summaries)
    attendance = 100 * attended / total_sessions if total_sessions else 0
    avg = sum(float(r["marks"]) for r in records) / len(records) if records else 0
    return f'''<section class="transcript panel"><div class="transcript-tools"><span>PRINT PREVIEW · CAMPUSDESK</span><button class="button primary" onclick="window.print()">Print / Save PDF</button></div>
      <div class="transcript-brand"><span class="brand-mark">C</span><div><strong>CampusDesk</strong><small>University Student Information System</small></div></div>
      <div class="transcript-title"><span class="eyebrow">ACADEMIC SERVICES</span><h2>Student course summary</h2><p>Academic progress and class attendance</p></div>
      <div class="student-meta"><div><small>STUDENT NAME</small><strong>{e(student['full_name'])}</strong></div><div><small>STUDENT ID</small><strong>{e(student['student_id'])}</strong></div><div><small>PROGRAM</small><strong>{e(student['program'])}</strong></div><div><small>SEMESTER</small><strong>{e(student['semester'])}</strong></div></div>
      <div class="transcript-stats"><div><small>COURSE RECORDS</small><strong>{len(records)}</strong></div><div><small>AVERAGE MARK</small><strong>{avg:.1f}%</strong></div><div><small>ATTENDANCE</small><strong>{attendance:.1f}%</strong></div></div>
      <h3>Course results</h3>{data_table(["Term", "Course code", "Course", "Marks", "Term attendance"], rows, "No course results have been entered.")}
      <p class="transcript-note">This report was generated from the local academic demonstration database. Sample names and results may be synthetic.</p></section>'''


def os_lab_page(operations, event_map, scheduling):
    rows = []
    for op in operations:
        events = event_map.get(op["operation_id"], [])
        timeline = " → ".join(e(x["state"]) for x in events)
        rows.append([f'<strong>{e(op["action"])}</strong><small class="sub-cell">{e(op["details"])}</small>', e(op["actor_role"]), f'<span class="mono">PID {e(op["os_pid"])}</span>', badge(op["status"]), f'<span class="state-trace">{timeline}</span>'])
    cards = "".join(f'<article class="schedule-card"><small>{e(a)}</small><strong>{float(w):.1f}</strong><span>avg wait · {float(t):.1f} turnaround</span></article>' for a, w, t in scheduling)
    return f'''<section class="page-toolbar"><p>Real CampusDesk saves are logged with process/thread IDs and operation states. Scheduling numbers below are a learning simulation.</p></section>
      <section class="panel"><div class="panel-heading"><div><h3>CPU scheduling comparison</h3><p>Same synthetic service-request workload, different scheduling policies</p></div></div><div class="schedule-grid">{cards}</div><div class="callout info"><strong>Learning model</strong><span>FCFS, Round Robin, and Priority are simulated for class. The real operating system still schedules this web server.</span></div></section>
      <section class="panel table-panel"><div class="panel-heading"><div><h3>Student-system operation traces</h3><p>Critical sections and database transactions for real app actions</p></div></div>{data_table(["User action", "Role", "Process", "Result", "Process states"], rows, "Save a student, marks, or attendance record to create an OS trace.")}</section>'''


def input_field(name, label, value="", kind="text", required=False, placeholder="", extra="", disabled=False):
    req = " required" if required else ""
    dis = " disabled" if disabled else ""
    return f'<div class="field"><label for="{e(name)}">{e(label)}</label><input id="{e(name)}" name="{e(name)}" type="{e(kind)}" value="{e(value)}" placeholder="{e(placeholder)}"{req}{dis} {extra}></div>'


def select_field(name, label, choices):
    return f'<div class="field"><label for="{e(name)}">{e(label)}</label><select id="{e(name)}" name="{e(name)}" required>{options(choices)}</select></div>'
