"""Class-session attendance and attendance percentage screen."""

from datetime import date
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database


class AttendancePage(ttk.Frame):
    def __init__(self, parent, db: Database, on_change) -> None:
        super().__init__(parent, padding=18)
        self.db, self.on_change = db, on_change
        self.role, self.student_id = "Administrator", ""
        self.selected_id: int | None = None
        self.course = tk.StringVar(); self.student = tk.StringVar()
        self.session_date = tk.StringVar(value=date.today().isoformat())
        self.status = tk.StringVar(value="Present")
        self.filter_course = tk.StringVar(value="All courses")
        self._build(); self.refresh_choices(); self.refresh()

    def _build(self) -> None:
        ttk.Label(self, text="Class attendance", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text="Mark attendance for each class date. Late counts as attended; Absent does not.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        self.form = ttk.LabelFrame(self, text="Mark a class session", padding=12); self.form.pack(fill="x", pady=(0, 12))
        specs = (("Student", self.student, 27, "choice"), ("Course", self.course, 23, "course"),
                 ("Class date (YYYY-MM-DD)", self.session_date, 16, "entry"), ("Status", self.status, 12, "status"))
        self.inputs = {}
        for col, (label, variable, width, kind) in enumerate(specs):
            ttk.Label(self.form, text=label).grid(row=0, column=col, sticky="w", padx=5)
            if kind == "choice":
                widget = ttk.Combobox(self.form, textvariable=variable, state="readonly", width=width)
            elif kind == "course":
                widget = ttk.Combobox(self.form, textvariable=variable, state="readonly", width=width)
                widget.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
            elif kind == "status":
                widget = ttk.Combobox(self.form, textvariable=variable, state="readonly", width=width,
                                      values=("Present", "Absent", "Late", "Excused"))
            else:
                widget = ttk.Entry(self.form, textvariable=variable, width=width)
            widget.grid(row=1, column=col, sticky="ew", padx=5, pady=(2, 8)); self.inputs[kind] = widget
            self.form.columnconfigure(col, weight=1)
        actions = ttk.Frame(self.form); actions.grid(row=2, column=0, columnspan=4, sticky="w", padx=5)
        self.save_button = ttk.Button(actions, text="Save attendance", command=self.save); self.save_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="Clear form", command=self.clear); self.clear_button.pack(side="left", padx=7)
        self.delete_button = ttk.Button(actions, text="Delete entry", command=self.delete); self.delete_button.pack(side="left")

        filters = ttk.Frame(self); filters.pack(fill="x", pady=(0, 7)); self.filters_frame = filters
        ttk.Label(filters, text="Show course").pack(side="left")
        self.filter_box = ttk.Combobox(filters, textvariable=self.filter_course, state="readonly", width=28)
        self.filter_box.pack(side="left", padx=7); self.filter_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.summary_text = ttk.Label(filters, text="", style="Muted.TLabel"); self.summary_text.pack(side="right")
        cols = ("id", "date", "student_id", "name", "course", "status")
        self.table = ttk.Treeview(self, columns=cols, show="headings", height=11)
        for col, label, width in zip(cols, ("#", "Class date", "Student ID", "Student", "Course", "Status"), (45, 120, 110, 210, 250, 100)):
            self.table.heading(col, text=label); self.table.column(col, width=width, anchor="w" if col in {"name", "course"} else "center")
        self.table.pack(fill="both", expand=True); self.table.bind("<<TreeviewSelect>>", self.select_row)
        ttk.Label(self, text="Attendance by course", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 4))
        self.summary_table = ttk.Treeview(self, columns=("student", "course", "attended", "total", "percent", "warning"), show="headings", height=5)
        for col, label, width in zip(("student", "course", "attended", "total", "percent", "warning"),
                                     ("Student", "Course", "Attended", "Sessions", "Rate", "Note"), (180, 210, 85, 85, 75, 200)):
            self.summary_table.heading(col, text=label); self.summary_table.column(col, width=width, anchor="w" if col in {"student", "course", "warning"} else "center")
        self.summary_table.pack(fill="x")

    def set_role(self, role: str, student_id: str = "") -> None:
        self.role, self.student_id = role, student_id
        if role == "Student": self.form.pack_forget()
        else: self.form.pack(fill="x", pady=(0, 12), before=self.filters_frame)
        enabled = role in {"Administrator", "Faculty"}
        self.save_button.configure(state="normal" if enabled else "disabled")
        self.clear_button.configure(state="normal" if enabled else "disabled")
        self.delete_button.configure(state="normal" if role == "Administrator" else "disabled")
        self.refresh_choices(); self.refresh()

    def refresh_choices(self) -> None:
        students = self.db.list_student_choices()
        courses = self.db.list_course_choices()
        self.inputs["choice"]["values"] = [f"{sid} — {name}" for sid, name in students]
        self.inputs["course"]["values"] = [f"{code} — {name}" for code, name in courses]
        course_labels = ["All courses"] + [f"{code} — {name}" for code, name in courses]
        self.filter_box["values"] = course_labels
        if self.filter_course.get() not in course_labels: self.filter_course.set("All courses")
        if self.role == "Student":
            self.student.set(next((f"{sid} — {name}" for sid, name in students if sid == self.student_id), ""))

    def refresh(self) -> None:
        course_code = self.filter_course.get().split(" — ", 1)[0] if self.filter_course.get() != "All courses" else ""
        rows = self.db.list_session_attendance(course_code, self.student_id if self.role == "Student" else "")
        for table in (self.table, self.summary_table):
            for item in table.get_children(): table.delete(item)
        for row in rows:
            self.table.insert("", "end", values=(row["attendance_id"], row["session_date"], row["student_id"], row["full_name"],
                                                  f"{row['course_code']} — {row['course_name']}", row["status"]))
        summaries = self.db.session_attendance_summary(self.student_id if self.role == "Student" else "")
        relevant = [r for r in summaries if not course_code or r["course_code"] == course_code]
        for row in relevant:
            rate = 100 * row["attended"] / row["total_sessions"] if row["total_sessions"] else 0
            warning = "Below 75%" if rate < 75 else ""
            self.summary_table.insert("", "end", values=(row["full_name"], f"{row['course_code']} — {row['course_name']}",
                row["attended"], row["total_sessions"], f"{rate:.1f}%", warning))
        low_count = sum(1 for row in relevant if row["total_sessions"] and 100 * row["attended"] / row["total_sessions"] < 75)
        if self.role == "Student":
            summary = f"{len(rows)} class entries · {low_count} of your course rates below 75%"
        else:
            summary = f"{len(rows)} class entries · {low_count} students below 75%"
        self.summary_text.configure(text=summary)

    def select_row(self, _event=None) -> None:
        selected = self.table.selection()
        if not selected: return
        row = self.table.item(selected[0], "values"); self.selected_id = int(row[0])
        self.session_date.set(row[1]); self.student.set(f"{row[2]} — {row[3]}")
        self.course.set(row[4]); self.status.set(row[5])

    def clear(self) -> None:
        self.selected_id = None
        if self.role != "Student": self.student.set("")
        self.course.set(""); self.session_date.set(date.today().isoformat()); self.status.set("Present")
        self.table.selection_remove(self.table.selection())

    def save(self) -> None:
        if self.role not in {"Administrator", "Faculty"}: return
        student_id = self.student.get().split(" — ", 1)[0]
        course_code = self.course.get().split(" — ", 1)[0]
        session_date = self.session_date.get().strip()
        if not student_id or not course_code:
            messagebox.showwarning("Missing information", "Choose a student and a course first."); return
        try:
            date.fromisoformat(session_date)
        except ValueError:
            messagebox.showerror("Check the date", "Enter the class date as YYYY-MM-DD."); return
        try:
            self.db.save_session_attendance({"student_id": student_id, "course_code": course_code,
                "session_date": session_date, "status": self.status.get()}, self.selected_id)
        except sqlite3.IntegrityError:
            messagebox.showerror("Attendance not saved", "That student already has attendance recorded for this course and date."); return
        except sqlite3.Error:
            messagebox.showerror("Attendance not saved", "The attendance could not be saved. Please try again."); return
        self.clear(); self.refresh(); self.on_change()

    def delete(self) -> None:
        if self.role != "Administrator": return
        if self.selected_id is None:
            messagebox.showinfo("Choose an entry", "Select a class attendance entry first."); return
        if messagebox.askyesno("Delete attendance", "Delete this class attendance entry?"):
            self.db.delete_session_attendance(self.selected_id); self.clear(); self.refresh(); self.on_change()
