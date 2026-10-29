"""Student directory CRUD page."""

import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import threading

from database import Database


class StudentsPage(ttk.Frame):
    def __init__(self, parent, db: Database, on_change) -> None:
        super().__init__(parent, padding=18)
        self.db, self.on_change = db, on_change
        self.role, self.student_id = "Administrator", ""
        self.selected_id: str | None = None
        self.search = tk.StringVar()
        self.vars = {key: tk.StringVar() for key in ("student_id", "full_name", "program", "semester", "email", "phone")}
        self.save_button: ttk.Button | None = None
        self.clear_button: ttk.Button | None = None
        self.delete_button: ttk.Button | None = None
        self.id_entry: ttk.Entry | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Students", style="Section.TLabel").pack(side="left")
        ttk.Label(top, text="Find a student").pack(side="left", padx=(28, 6))
        search = ttk.Entry(top, textvariable=self.search, width=30)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda _e: self.refresh())
        ttk.Button(top, text="Clear search", command=lambda: (self.search.set(""), self.refresh())).pack(side="left", padx=6)

        form = ttk.LabelFrame(self, text="Student information", padding=12)
        self.form = form
        form.pack(fill="x", pady=(0, 12))
        fields = [("student_id", "Student ID"), ("full_name", "Full name"), ("program", "Program"),
                  ("semester", "Semester"), ("email", "Email"), ("phone", "Phone")]
        for i, (key, label) in enumerate(fields):
            row, col = divmod(i, 3)
            ttk.Label(form, text=label).grid(row=row * 2, column=col, sticky="w", padx=6)
            entry = ttk.Entry(form, textvariable=self.vars[key], width=28)
            entry.grid(row=row * 2 + 1, column=col, sticky="ew", padx=6, pady=(2, 8))
            if key == "student_id":
                self.id_entry = entry
            form.columnconfigure(col, weight=1)
        actions = ttk.Frame(form)
        actions.grid(row=4, column=0, columnspan=3, sticky="w", padx=6)
        self.save_button = ttk.Button(actions, text="Add student", command=self.save)
        self.save_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="Add another student", command=self.clear)
        self.clear_button.pack(side="left", padx=7)
        self.delete_button = ttk.Button(actions, text="Delete student", command=self.delete)
        self.delete_button.pack(side="left")
        ttk.Label(form, text="Student ID stays the same when you edit a saved student.", style="Muted.TLabel").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=6, pady=(6, 0))

        columns = ("student_id", "full_name", "program", "semester", "email", "phone")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=13)
        labels = ("Student ID", "Full name", "Program", "Semester", "Email", "Phone")
        widths = (100, 180, 130, 75, 210, 110)
        for col, label, width in zip(columns, labels, widths):
            self.table.heading(col, text=label)
            self.table.column(col, width=width, anchor="w" if col in {"full_name", "program", "email"} else "center")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.select_row)

    def refresh(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)
        for student in self.db.list_students_for(self.search.get(), self.student_id if self.role == "Student" else ""):
            self.table.insert("", "end", values=tuple(student[k] for k in ("student_id", "full_name", "program", "semester", "email", "phone")))

    def set_role(self, role: str, student_id: str = "") -> None:
        self.role, self.student_id = role, student_id
        if role == "Administrator":
            self.form.pack(fill="x", pady=(0, 12), before=self.table)
        else:
            self.form.pack_forget()
        self.refresh()

    def select_row(self, _event=None) -> None:
        chosen = self.table.selection()
        if not chosen:
            return
        values = self.table.item(chosen[0], "values")
        self.selected_id = values[0]
        self.save_button.configure(text="Save changes")
        self.id_entry.configure(state="readonly")
        for key, value in zip(self.vars, values):
            self.vars[key].set(value)

    def clear(self) -> None:
        self.selected_id = None
        self.save_button.configure(text="Add student")
        self.id_entry.configure(state="normal")
        for value in self.vars.values():
            value.set("")
        self.table.selection_remove(self.table.selection())

    def save(self) -> None:
        if self.role != "Administrator":
            return
        data = {key: self.vars[key].get().strip() for key in self.vars}
        if not all(data[k] for k in ("student_id", "full_name", "program", "semester", "email")):
            messagebox.showwarning("Missing information", "Please enter the student's ID, name, program, semester, and email.")
            return
        try:
            data["semester"] = int(data["semester"])
            if not 1 <= data["semester"] <= 12:
                raise ValueError("Semester must be between 1 and 12.")
        except ValueError as exc:
            messagebox.showerror("Check the semester", str(exc))
            return
        original_id = self.selected_id
        self.save_button.configure(state="disabled", text="Saving…")
        self.clear_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.table.state(["disabled"])

        def save_in_background() -> None:
            error = None
            try:
                self.db.save_student(data, original_id)
            except Exception as exc:
                error = exc
            self.after(0, lambda saved_error=error: self._finish_save(saved_error))

        threading.Thread(target=save_in_background, name="save-student", daemon=True).start()

    def _finish_save(self, error: Exception | None) -> None:
        self.save_button.configure(state="normal", text="Save changes" if self.selected_id else "Add student")
        self.clear_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.table.state(["!disabled"])
        if isinstance(error, sqlite3.IntegrityError):
            details = str(error).lower()
            if "unique" in details and "email" in details:
                message = "That email address is already used by another student. Check the address and try again."
            elif "unique" in details and "student_id" in details:
                message = "A student with that ID already exists. Choose a different ID."
            elif "foreign key" in details:
                message = "This student is linked to course records, so their ID cannot be changed. Select the student and edit their other details instead."
            else:
                message = "Some information conflicts with an existing record. Check the student ID and email, then try again."
            messagebox.showerror("Student could not be saved", message)
            self.on_change()
            return
        if isinstance(error, sqlite3.Error):
            messagebox.showerror("Student could not be saved", "The database could not save this student. Please try again.")
            self.on_change()
            return
        if error:
            messagebox.showerror("Student could not be saved", "The student could not be saved. Please try again.")
            self.on_change()
            return
        self.clear()
        self.refresh()
        self.on_change()

    def delete(self) -> None:
        if self.role != "Administrator":
            return
        if not self.selected_id:
            messagebox.showinfo("Choose a student", "Select a student from the list before deleting.")
            return
        if messagebox.askyesno("Delete student", f"Delete {self.selected_id} and its linked academic records?"):
            try:
                self.db.delete_student(self.selected_id)
            except Exception as exc:
                messagebox.showerror("Student could not be deleted", "The student record could not be deleted. Please try again.")
                self.on_change()
                return
            self.clear()
            self.refresh()
            self.on_change()
