"""Course catalog management screen."""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database


class CoursesPage(ttk.Frame):
    def __init__(self, parent, db: Database, on_change) -> None:
        super().__init__(parent, padding=18)
        self.db, self.on_change = db, on_change
        self.role = "Administrator"
        self.selected_code: str | None = None
        self.search = tk.StringVar()
        self.values = {key: tk.StringVar() for key in ("course_code", "course_name", "department", "credits", "semester")}
        self.form = ttk.LabelFrame(self, text="Course details", padding=12)
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self); top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="Course catalog", style="Section.TLabel").pack(side="left")
        ttk.Label(top, text="Find a course").pack(side="left", padx=(24, 6))
        entry = ttk.Entry(top, textvariable=self.search, width=30); entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda _e: self.refresh())
        self.form.pack(fill="x", pady=(0, 12))
        fields = (("course_code", "Course code", 18), ("course_name", "Course name", 26),
                  ("department", "Department", 20), ("credits", "Credits", 10), ("semester", "Semester", 10))
        self.entries = {}
        for col, (key, label, width) in enumerate(fields):
            ttk.Label(self.form, text=label).grid(row=0, column=col, sticky="w", padx=5)
            item = ttk.Entry(self.form, textvariable=self.values[key], width=width)
            item.grid(row=1, column=col, sticky="ew", padx=5, pady=(2, 8)); self.entries[key] = item
            self.form.columnconfigure(col, weight=1)
        actions = ttk.Frame(self.form); actions.grid(row=2, column=0, columnspan=5, sticky="w", padx=5)
        self.save_button = ttk.Button(actions, text="Add course", command=self.save); self.save_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="Add another course", command=self.clear); self.clear_button.pack(side="left", padx=7)
        self.delete_button = ttk.Button(actions, text="Delete course", command=self.delete); self.delete_button.pack(side="left")
        ttk.Label(self.form, text="Course code cannot be changed after records refer to it.", style="Muted.TLabel").grid(
            row=3, column=0, columnspan=5, sticky="w", padx=5, pady=(5, 0))
        cols = ("course_code", "course_name", "department", "credits", "semester")
        self.table = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for col, label, width in zip(cols, ("Course code", "Course name", "Department", "Credits", "Semester"), (130, 260, 210, 90, 90)):
            self.table.heading(col, text=label); self.table.column(col, width=width, anchor="w" if col in {"course_name", "department"} else "center")
        self.table.pack(fill="both", expand=True); self.table.bind("<<TreeviewSelect>>", self.select_row)

    def set_role(self, role: str) -> None:
        self.role = role
        if role == "Administrator":
            self.form.pack(fill="x", pady=(0, 12), before=self.table)
        else:
            self.form.pack_forget()

    def refresh(self) -> None:
        for row in self.table.get_children(): self.table.delete(row)
        for course in self.db.list_courses(self.search.get()):
            self.table.insert("", "end", values=tuple(course[k] for k in ("course_code", "course_name", "department", "credits", "semester")))

    def select_row(self, _event=None) -> None:
        selected = self.table.selection()
        if not selected: return
        row = self.table.item(selected[0], "values"); self.selected_code = row[0]
        for key, value in zip(self.values, row): self.values[key].set(value)
        self.save_button.configure(text="Save changes")
        self.entries["course_code"].configure(state="readonly")

    def clear(self) -> None:
        self.selected_code = None
        for value in self.values.values(): value.set("")
        self.entries["course_code"].configure(state="normal")
        self.save_button.configure(text="Add course")
        self.table.selection_remove(self.table.selection())

    def save(self) -> None:
        if self.role != "Administrator": return
        data = {key: value.get().strip() for key, value in self.values.items()}
        if not all(data.values()):
            messagebox.showwarning("Missing information", "Fill in all course details."); return
        try:
            data["course_code"] = data["course_code"].upper()
            data["credits"], data["semester"] = int(data["credits"]), int(data["semester"])
            if not 1 <= data["credits"] <= 10 or not 1 <= data["semester"] <= 12:
                raise ValueError
            self.db.save_course(data, self.selected_code)
        except ValueError:
            messagebox.showerror("Check course details", "Credits must be 1–10 and semester must be 1–12."); return
        except sqlite3.IntegrityError:
            messagebox.showerror("Course not saved", "That course code is already in the catalog."); return
        except Exception:
            messagebox.showerror("Course not saved", "The course could not be saved. Please check the details."); return
        self.clear(); self.refresh(); self.on_change()

    def delete(self) -> None:
        if self.role != "Administrator": return
        if not self.selected_code:
            messagebox.showinfo("Choose a course", "Select a course from the list first."); return
        if not messagebox.askyesno("Delete course", f"Delete {self.selected_code} from the catalog?"): return
        try:
            self.db.delete_course(self.selected_code)
        except ValueError as exc:
            messagebox.showerror("Course is in use", str(exc)); return
        except sqlite3.Error:
            messagebox.showerror("Course not deleted", "The course could not be deleted."); return
        self.clear(); self.refresh(); self.on_change()
