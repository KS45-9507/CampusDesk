"""Main desktop application for the University Student Information System."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from database import Database
from attendance_page import AttendancePage
from courses_page import CoursesPage
from concurrency_page import ConcurrencyPage
from os_lab_page import OSLabPage
from records_page import RecordsPage
from students_page import StudentsPage


class StudentInformationApp(tk.Tk):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.role_var = tk.StringVar(value="Administrator")
        self.student_profile_var = tk.StringVar()
        self.role = "Administrator"
        self.student_profile_map = {}
        self.title("CampusDesk | Student and Course Records")
        self.geometry("1280x800")
        self.minsize(1080, 680)
        self.configure(bg="#f2f5f8")
        self._configure_styles()
        self._build_shell()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f5f8")
        style.configure("TLabel", background="#f2f5f8", foreground="#203040", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground="#607080", font=("Segoe UI", 9))
        style.configure("Section.TLabel", font=("Segoe UI", 16, "bold"), foreground="#17324d")
        style.configure("PageTitle.TLabel", font=("Segoe UI", 22, "bold"), foreground="#142b43")
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TNotebook", background="#f2f5f8", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 9), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#17324d")])
        style.configure("TButton", padding=(11, 7), font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", background="#e8eef4", foreground="#24425e", padding=(8, 8))

    def _build_shell(self) -> None:
        shell = tk.Frame(self, bg="#f2f5f8")
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg="#132b43", width=235)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="CampusDesk", bg="#132b43", fg="white", font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=22, pady=(26, 2))
        tk.Label(self.sidebar, text="UNIVERSITY SIS", bg="#132b43", fg="#9cb4ca", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=24, pady=(0, 25))
        self.nav = tk.Frame(self.sidebar, bg="#132b43")
        self.nav.pack(fill="x", padx=12)
        self.sidebar_footer = tk.Label(self.sidebar, text="ADMIN WORKSPACE", bg="#132b43", fg="#7893ab", font=("Segoe UI", 8, "bold"))
        self.sidebar_footer.pack(side="bottom", anchor="w", padx=23, pady=20)
        main = tk.Frame(shell, bg="#f2f5f8")
        main.pack(side="left", fill="both", expand=True)
        header = tk.Frame(main, bg="white", padx=25, pady=13, highlightbackground="#dce3e9", highlightthickness=1)
        header.pack(fill="x")
        tk.Label(header, text="Student and course records", bg="white", fg="#496176", font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(header, text="LOCAL DEMO", bg="#e8f0f7", fg="#24425e", padx=9, pady=5,
                 font=("Segoe UI", 8, "bold")).pack(side="right")
        tk.Label(header, text="Preview role", bg="white", fg="#566d81", font=("Segoe UI", 9)).pack(side="right", padx=(12, 6))
        self.role_box = ttk.Combobox(header, textvariable=self.role_var, state="readonly", width=17,
                                     values=("Administrator", "Faculty", "Student"))
        self.role_box.pack(side="right")
        self.role_box.bind("<<ComboboxSelected>>", self._role_changed)
        self.student_profile_box = ttk.Combobox(header, textvariable=self.student_profile_var, state="readonly", width=25)
        self.student_profile_box.bind("<<ComboboxSelected>>", self._role_changed)
        self.profile_label = tk.Label(header, text="Student profile", bg="white", fg="#566d81", font=("Segoe UI", 9))
        self.workspace = tk.Frame(main, bg="#f2f5f8", padx=20, pady=18)
        self.workspace.pack(fill="both", expand=True)
        self.dashboard = ttk.Frame(self.workspace, padding=10)
        self.students_page = StudentsPage(self.workspace, self.db, self.refresh_dashboard)
        self.courses_page = CoursesPage(self.workspace, self.db, self.refresh_dashboard)
        self.records_page = RecordsPage(self.workspace, self.db, self.refresh_dashboard)
        self.attendance_page = AttendancePage(self.workspace, self.db, self.refresh_dashboard)
        self.os_page = OSLabPage(self.workspace, self.db)
        self.concurrency_page = ConcurrencyPage(self.workspace, self.db)
        self.pages = {"Home": self.dashboard, "Students": self.students_page, "Course catalog": self.courses_page,
                      "Courses and marks": self.records_page, "Class attendance": self.attendance_page,
                      "OS concepts": self.os_page, "Concurrency lab": self.concurrency_page}
        self.current_page = "Home"
        self._refresh_student_profiles()
        self._apply_role()
        self.refresh_dashboard()

    def _show_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        for child in self.workspace.winfo_children():
            child.pack_forget()
        page.pack(fill="both", expand=True)
        self.current_page = key
        for name, button in getattr(self, "nav_buttons", {}).items():
            active = name == key
            button.configure(bg="#294764" if active else "#132b43", fg="white" if active else "#c5d3df")

    def _build_role_navigation(self) -> None:
        for child in self.nav.winfo_children():
            child.destroy()
        self.nav_buttons = {}
        sections = [("WORKSPACE", ["Home", "Students", "Course catalog", "Courses and marks", "Class attendance"])]
        if self.role in {"Administrator", "Faculty"}:
            sections.append(("OS CONCEPTS", ["OS concepts", "Concurrency lab"]))
        for heading, pages in sections:
            tk.Label(self.nav, text=heading, bg="#132b43", fg="#7893ab", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(13, 6))
            for key in pages:
                labels = {"Home": "Overview", "Students": "My profile" if self.role == "Student" else "Student directory",
                          "Course catalog": "Course catalog", "Courses and marks": "My courses and marks" if self.role == "Student" else "Courses and marks",
                          "Class attendance": "My attendance" if self.role == "Student" else "Class attendance",
                          "OS concepts": "Process scheduling", "Concurrency lab": "Concurrency and locks"}
                button = tk.Button(self.nav, text=labels[key], anchor="w", relief="flat", borderwidth=0,
                                   bg="#132b43", fg="#c5d3df", activebackground="#294764", activeforeground="white",
                                   font=("Segoe UI", 10), padx=12, pady=10, cursor="hand2",
                                   command=lambda page=key: self._show_page(page))
                button.pack(fill="x", pady=2)
                self.nav_buttons[key] = button
        self._show_page(self.current_page if self.current_page in self.nav_buttons else "Home")

    def _refresh_student_profiles(self) -> None:
        choices = self.db.list_student_choices()
        self.student_profile_map = {f"{sid} — {name}": sid for sid, name in choices}
        self.student_profile_box["values"] = list(self.student_profile_map)
        if self.student_profile_var.get() not in self.student_profile_map:
            self.student_profile_var.set(next(iter(self.student_profile_map), ""))

    def _role_changed(self, _event=None) -> None:
        self._refresh_student_profiles()
        self._apply_role()
        self.refresh_dashboard()

    def _apply_role(self) -> None:
        self.role = self.role_var.get()
        self.sidebar_footer.configure(text=f"{self.role.upper()} WORKSPACE")
        student_id = self.student_profile_map.get(self.student_profile_var.get(), "") if self.role == "Student" else ""
        self.db.set_access_context(self.role, student_id)
        if self.role == "Student":
            self.profile_label.pack(side="right", padx=(14, 5))
            self.student_profile_box.pack(side="right", padx=5)
        else:
            self.student_profile_box.pack_forget(); self.profile_label.pack_forget()
        self.students_page.set_role(self.role, student_id)
        self.courses_page.set_role(self.role)
        self.records_page.set_role(self.role, student_id)
        self.attendance_page.set_role(self.role, student_id)
        if self.role == "Student":
            self.pages["Students"] = self.students_page
            self.pages["Course catalog"] = self.courses_page
        self._build_role_navigation()
        if getattr(self, "backup_button", None) and self.backup_button.winfo_exists():
            if self.role == "Administrator":
                self.backup_button.pack(side="right", padx=8)
                self.export_button.pack(side="right")
            else:
                self.backup_button.pack_forget()
                self.export_button.pack_forget()

    def refresh_dashboard(self) -> None:
        if hasattr(self, "records_page"):
            self.records_page.refresh_choices()
            self.records_page.refresh()
        if hasattr(self, "courses_page"):
            self.courses_page.refresh()
        if hasattr(self, "attendance_page"):
            self.attendance_page.refresh_choices()
            self.attendance_page.refresh()
        if hasattr(self, "concurrency_page"):
            self.concurrency_page.refresh_operations()
        for child in self.dashboard.winfo_children():
            child.destroy()
        self.backup_button = None
        self.export_button = None
        student_id = self.student_profile_map.get(self.student_profile_var.get(), "") if self.role == "Student" else ""
        data = self.db.summary(student_id=student_id)
        welcome = "Your student information" if self.role == "Student" else f"Welcome, {self.role}"
        ttk.Label(self.dashboard, text=welcome, style="Section.TLabel").pack(anchor="w")
        subtitles = {"Administrator": "Manage the student directory, course catalog, marks, and attendance.",
                     "Faculty": "Review student progress, enter marks, and record class attendance.",
                     "Student": "View your profile, course results, and class attendance."}
        subtitle = subtitles[self.role]
        ttk.Label(self.dashboard, text=subtitle,
                  style="Muted.TLabel").pack(anchor="w", pady=(4, 16))

        cards = ttk.Frame(self.dashboard)
        cards.pack(fill="x", pady=(0, 18))
        stats = ([ ("My profile", "Ready"), ("My course records", str(data["records"])),
                   ("Average mark", f'{data["avg_marks"]:.1f}%'), ("Course attendance", f'{data["avg_attendance"]:.1f}%') ]
                 if self.role == "Student" else
                 [("Students", str(data["students"])), ("Course records", str(data["records"])),
                  ("Average mark", f'{data["avg_marks"]:.1f}%'), ("Average attendance", f'{data["avg_attendance"]:.1f}%')])
        for i, (label, value) in enumerate(stats):
            card = tk.Frame(cards, bg="white", padx=17, pady=15, highlightbackground="#dce3e9", highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            tk.Label(card, text=label.upper(), bg="white", fg="#657585", font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(card, text=value, bg="white", fg="#17324d", font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(6, 0))
            cards.columnconfigure(i, weight=1)

        quick = ttk.Frame(self.dashboard)
        quick.pack(fill="x", pady=(0, 18))
        ttk.Button(quick, text="Manage students" if self.role == "Administrator" else "My profile" if self.role == "Student" else "View student list",
                   command=lambda: self._show_page("Students")).pack(side="left")
        ttk.Button(quick, text="My courses and marks" if self.role == "Student" else "Enter marks" if self.role == "Faculty" else "View course records",
                   command=lambda: self._show_page("Courses and marks")).pack(side="left", padx=8)
        if self.role != "Student":
            ttk.Button(quick, text="Mark attendance", command=lambda: self._show_page("Class attendance")).pack(side="left")
            ttk.Button(quick, text="See OS action traces", command=lambda: self._show_page("Concurrency lab")).pack(side="left", padx=8)
        if self.role != "Student":
            ttk.Button(quick, text="See how it works", command=lambda: self._show_page("OS concepts")).pack(side="left", padx=8)
        if self.role != "Student":
            self.export_button = ttk.Button(quick, text="Export course records", command=self.export_records)
            self.export_button.pack(side="right")
            self.backup_button = ttk.Button(quick, text="Save a backup", command=self.backup_database)
            self.backup_button.pack(side="right", padx=8)

        insights = ttk.Frame(self.dashboard)
        insights.pack(fill="x", pady=(0, 12))
        chart_card = tk.Frame(insights, bg="white", padx=16, pady=12, highlightbackground="#dce3e9", highlightthickness=1)
        chart_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(chart_card, text="COURSE PERFORMANCE", bg="white", fg="#526a7e", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        chart = tk.Canvas(chart_card, height=200, bg="white", highlightthickness=0)
        chart.pack(fill="both", expand=True, pady=(5, 0))
        performance = self.db.course_performance_summary(student_id)
        chart.bind("<Configure>", lambda event, widget=chart, rows=performance: self._draw_performance_chart(widget, rows))

        attendance_card = tk.Frame(insights, bg="white", padx=16, pady=12, highlightbackground="#dce3e9", highlightthickness=1)
        attendance_card.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(attendance_card, text="ATTENDANCE CHECK", bg="white", fg="#526a7e", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        session_summary = self.db.session_attendance_summary(student_id)
        low = [row for row in session_summary if row["total_sessions"] and 100 * row["attended"] / row["total_sessions"] < 75]
        if not session_summary:
            status_text, status_color = "No class sessions recorded yet", "#607080"
        elif low:
            status_text, status_color = f"{len(low)} course rate(s) below 75%", "#b5473c"
        else:
            status_text, status_color = "All recorded course rates are at least 75%", "#24815b"
        tk.Label(attendance_card, text=status_text, bg="white", fg=status_color, font=("Segoe UI", 14, "bold"),
                 wraplength=390, justify="left").pack(anchor="w", pady=(17, 7))
        total_sessions = sum(row["total_sessions"] for row in session_summary)
        total_attended = sum(row["attended"] for row in session_summary)
        overall_rate = 100 * total_attended / total_sessions if total_sessions else 0
        tk.Label(attendance_card, text=f"{total_attended} of {total_sessions} sessions attended  ·  {overall_rate:.1f}% overall",
                 bg="white", fg="#526a7e", font=("Segoe UI", 10)).pack(anchor="w")
        if low:
            tk.Label(attendance_card, text="Below 75%: " + ", ".join(row["course_code"] for row in low[:4]),
                     bg="white", fg="#a53e34", font=("Segoe UI", 9)).pack(anchor="w", pady=(13, 0))

        if self.role == "Administrator":
            ttk.Label(self.dashboard, text="Recent changes", style="Section.TLabel").pack(anchor="w", pady=(5, 8))
            log = ttk.Treeview(self.dashboard, columns=("when", "action", "details"), show="headings", height=6)
            for col, label, width in (("when", "When", 185), ("action", "What changed", 175), ("details", "Details", 570)):
                log.heading(col, text=label); log.column(col, width=width, anchor="w")
            log.pack(fill="x")
            for entry in data["recent"]:
                log.insert("", "end", values=(entry["happened_at"].replace("T", " "), entry["action"], entry["details"]))
        ttk.Label(self.dashboard, text=f"Data is saved on this computer: {self.db.path.resolve()}  ·  Sample names are examples.",
                  style="Muted.TLabel").pack(anchor="w", pady=(12, 0))

    @staticmethod
    def _draw_performance_chart(canvas: tk.Canvas, rows) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 190)
        left, right, top, bottom = 10, width - 14, 12, height - 34
        canvas.create_line(left, bottom, right, bottom, fill="#dce3e9")
        if not rows:
            canvas.create_text(width / 2, height / 2, text="Course results will appear here", fill="#607080",
                               font=("Segoe UI", 10))
            return
        visible = rows[:6]
        slot = (right - left) / len(visible)
        for i, row in enumerate(visible):
            value = float(row["average_marks"] or 0)
            bar_h = (bottom - top) * value / 100
            x0 = left + i * slot + slot * .22
            x1 = left + (i + 1) * slot - slot * .22
            y0 = bottom - bar_h
            color = "#3d8b75" if value >= 75 else "#d29a46" if value >= 60 else "#c76559"
            canvas.create_rectangle(x0, y0, x1, bottom, fill=color, outline="")
            canvas.create_text((x0 + x1) / 2, max(y0 - 10, top), text=f"{value:.0f}%", fill="#31485e",
                               font=("Segoe UI", 9, "bold"))
            canvas.create_text((x0 + x1) / 2, bottom + 16, text=row["course_code"], fill="#526a7e",
                               font=("Segoe UI", 8))

    def backup_database(self) -> None:
        destination = filedialog.asksaveasfilename(title="Save database backup", defaultextension=".db",
            filetypes=(("SQLite database", "*.db"), ("All files", "*.*")), initialfile="student_information_backup.db")
        if not destination:
            return
        try:
            saved = self.db.create_backup(destination)
            self.refresh_dashboard()
            messagebox.showinfo("Backup created", f"Database backup saved to:\n{saved}")
        except Exception as exc:
            messagebox.showerror("Backup failed", str(exc))

    def export_records(self) -> None:
        destination = filedialog.asksaveasfilename(title="Export academic records", defaultextension=".csv",
            filetypes=(("CSV file", "*.csv"), ("All files", "*.*")), initialfile="academic_records.csv")
        if not destination:
            return
        try:
            saved = self.db.export_academic_records(destination)
            self.refresh_dashboard()
            messagebox.showinfo("Export complete", f"Academic records exported to:\n{saved}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
