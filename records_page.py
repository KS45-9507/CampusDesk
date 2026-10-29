"""Academic record management page."""

import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import threading

from database import Database


class RecordsPage(ttk.Frame):
    def __init__(self, parent, db: Database, on_change) -> None:
        super().__init__(parent, padding=18)
        self.db, self.on_change = db, on_change
        self.role, self.student_id = "Administrator", ""
        self.selected_id: int | None = None
        self.search = tk.StringVar()
        self.student = tk.StringVar()
        self.course_code = tk.StringVar()
        self.course_name = tk.StringVar()
        self.term = tk.StringVar(value="Semester 3")
        self.attendance = tk.StringVar()
        self.marks = tk.StringVar()
        self.save_button: ttk.Button | None = None
        self.clear_button: ttk.Button | None = None
        self.delete_button: ttk.Button | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Course results and attendance", style="Section.TLabel").pack(side="left")
        ttk.Label(top, text="Find by student or course").pack(side="left", padx=(26, 6))
        search = ttk.Entry(top, textvariable=self.search, width=30)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda _e: self.refresh())

        form = ttk.LabelFrame(self, text="Add or edit a course record", padding=12)
        self.form = form
        form.pack(fill="x", pady=(0, 12))
        ttk.Label(form, text="Choose a student").grid(row=0, column=0, sticky="w", padx=5)
        self.student_box = ttk.Combobox(form, textvariable=self.student, state="readonly", width=25)
        self.student_box.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 8))
        for col, (label, var, width) in enumerate((("Choose a course", self.course_code, 25), ("Course name", self.course_name, 24),
                                                   ("Term", self.term, 16), ("Attendance %", self.attendance, 12), ("Marks %", self.marks, 10)), 1):
            ttk.Label(form, text=label).grid(row=0, column=col, sticky="w", padx=5)
            if label == "Choose a course":
                widget = ttk.Combobox(form, textvariable=var, state="readonly", width=width)
                widget.bind("<<ComboboxSelected>>", self._course_selected)
                self.course_box = widget
            else:
                widget = ttk.Entry(form, textvariable=var, width=width, state="readonly" if label == "Course name" else "normal")
            widget.grid(row=1, column=col, sticky="ew", padx=5, pady=(2, 8))
        actions = ttk.Frame(form)
        actions.grid(row=2, column=0, columnspan=6, sticky="w", padx=5)
        self.save_button = ttk.Button(actions, text="Save course record", command=self.save)
        self.save_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="Clear form", command=self.clear)
        self.clear_button.pack(side="left", padx=7)
        self.delete_button = ttk.Button(actions, text="Delete course record", command=self.delete)
        self.delete_button.pack(side="left")
        form.columnconfigure(0, weight=1)

        columns = ("id", "student_id", "full_name", "course_code", "course_name", "term", "attendance", "marks")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=14)
        labels = ("#", "Student ID", "Student name", "Course", "Course name", "Term", "Attendance", "Marks")
        widths = (45, 90, 150, 100, 190, 100, 90, 70)
        for col, label, width in zip(columns, labels, widths):
            self.table.heading(col, text=label)
            self.table.column(col, width=width, anchor="w" if col in {"full_name", "course_name"} else "center")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.select_row)
        self.refresh_choices()

    def refresh_choices(self) -> None:
        self.choices = self.db.list_student_choices()
        self.student_box["values"] = [f"{sid} — {name}" for sid, name in self.choices]
        self.courses = dict(self.db.list_course_choices())
        self.course_box["values"] = [f"{code} — {name}" for code, name in self.courses.items()]

    def _course_selected(self, _event=None) -> None:
        code = self.course_code.get().split(" — ", 1)[0]
        self.course_name.set(self.courses.get(code, ""))

    def refresh(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)
        for record in self.db.list_records_for(self.search.get(), self.student_id if self.role == "Student" else ""):
            self.table.insert("", "end", values=(record["record_id"], record["student_id"], record["full_name"],
                record["course_code"], record["course_name"], record["term"], f'{record["attendance"]:.1f}%', f'{record["marks"]:.1f}%'))

    def set_role(self, role: str, student_id: str = "") -> None:
        self.role, self.student_id = role, student_id
        if role == "Student": self.form.pack_forget()
        else: self.form.pack(fill="x", pady=(0, 12), before=self.table)
        self.save_button.configure(state="disabled" if role == "Student" else "normal")
        self.clear_button.configure(state="disabled" if role == "Student" else "normal")
        self.delete_button.configure(state="normal" if role == "Administrator" else "disabled")
        self.refresh_choices(); self.refresh()

    def select_row(self, _event=None) -> None:
        chosen = self.table.selection()
        if not chosen:
            return
        row = self.table.item(chosen[0], "values")
        self.selected_id = int(row[0])
        self.student.set(f"{row[1]} — {row[2]}")
        self.course_code.set(f"{row[3]} — {row[4]}"); self.course_name.set(row[4]); self.term.set(row[5])
        self.attendance.set(str(row[6]).rstrip("%")); self.marks.set(str(row[7]).rstrip("%"))

    def clear(self) -> None:
        self.selected_id = None
        for variable in (self.student, self.course_code, self.course_name, self.attendance, self.marks):
            variable.set("")
        self.term.set("Semester 3")
        self.table.selection_remove(self.table.selection())

    def save(self) -> None:
        if self.role not in {"Administrator", "Faculty"}: return
        student_id = self.student.get().split(" — ", 1)[0]
        course_code = self.course_code.get().split(" — ", 1)[0]
        if not student_id or not all(v.get().strip() for v in (self.course_code, self.course_name, self.term, self.attendance, self.marks)):
            messagebox.showwarning("Missing information", "Choose a student and course, then fill in the term, attendance, and marks.")
            return
        if course_code not in self.courses:
            messagebox.showwarning("Choose a course", "Add this course to the course catalog before entering marks.")
            return
        try:
            attendance, marks = float(self.attendance.get()), float(self.marks.get())
            if not 0 <= attendance <= 100 or not 0 <= marks <= 100:
                raise ValueError("Attendance and marks must be between 0 and 100.")
        except ValueError:
            messagebox.showerror("Check the numbers", "Attendance and marks must be numbers from 0 to 100.")
            return
        data = {"student_id": student_id, "course_code": course_code.strip().upper(),
                "course_name": self.courses[course_code], "term": self.term.get().strip(),
                "attendance": attendance, "marks": marks}
        record_id = self.selected_id
        self.save_button.configure(state="disabled", text="Saving…")
        self.clear_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.table.state(["disabled"])

        def save_in_background() -> None:
            error = None
            try:
                self.db.save_record(data, record_id)
            except Exception as exc:
                error = exc
            self.after(0, lambda saved_error=error: self._finish_save(saved_error))

        threading.Thread(target=save_in_background, name="save-course-record", daemon=True).start()

    def _finish_save(self, error: Exception | None) -> None:
        self.save_button.configure(state="normal", text="Save course record")
        self.clear_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.table.state(["!disabled"])
        if isinstance(error, sqlite3.IntegrityError):
            if "unique" in str(error).lower():
                message = "This student already has a record for that course and term. Edit the existing record instead."
            else:
                message = "The course record conflicts with saved information. Check your entries and try again."
            messagebox.showerror("Course record could not be saved", message)
            self.on_change()
            return
        if isinstance(error, sqlite3.Error):
            messagebox.showerror("Course record could not be saved", "The database could not save this record. Please try again.")
            self.on_change()
            return
        if error:
            messagebox.showerror("Course record could not be saved", "The course record could not be saved. Please try again.")
            self.on_change()
            return
        self.clear(); self.refresh(); self.on_change()

    def delete(self) -> None:
        if self.role != "Administrator": return
        if self.selected_id is None:
            messagebox.showinfo("Choose a course record", "Select a course record from the list first.")
            return
        if messagebox.askyesno("Delete course record", "Delete the selected course record?"):
            try:
                self.db.delete_record(self.selected_id)
            except sqlite3.Error:
                messagebox.showerror("Course record could not be deleted", "The record could not be deleted. Please try again.")
                self.on_change()
                return
            self.clear(); self.refresh(); self.on_change()
