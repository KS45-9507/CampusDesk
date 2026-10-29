"""OS concepts lab: CPU scheduling and basic process/thread observations."""

import os
import platform
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from database import Database
from models import Request
from sample_data import sample_requests
from scheduler import SimulationResult, simulate


class OSLabPage(ttk.Frame):
    def __init__(self, parent, db: Database) -> None:
        super().__init__(parent, padding=18)
        self.db = db
        self.requests = sample_requests()
        self.algorithm = tk.StringVar(value="Round Robin")
        self.quantum = tk.StringVar(value="2")
        self._build()
        self.run_simulation()

    def _build(self) -> None:
        ttk.Label(self, text="How the computer runs this app", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text="Compare how the CPU might order CampusDesk actions. CPU time values are estimates, not measurements.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))
        workload = ttk.Frame(self)
        workload.pack(fill="x", pady=(0, 8))
        ttk.Button(workload, text="Use my recent SIS actions", command=self.load_recent_actions).pack(side="left")
        self.workload_note = ttk.Label(workload, text="Showing example student, marks, and report actions.", style="Muted.TLabel")
        self.workload_note.pack(side="left", padx=10)

        system = ttk.LabelFrame(self, text="About this computer", padding=12)
        system.pack(fill="x", pady=(0, 12))
        self.system_info = ttk.Label(system, text=self._system_summary(), justify="left")
        self.system_info.pack(side="left", anchor="w")
        self.thread_button = ttk.Button(system, text="Load students in background", command=self.run_background_task)
        self.thread_button.pack(side="right")
        self.thread_result = ttk.Label(system, text="", style="Muted.TLabel")
        self.thread_result.pack(side="right", padx=12)

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 10))
        ttk.Label(controls, text="Request order").pack(side="left")
        self.selector = ttk.Combobox(controls, textvariable=self.algorithm, state="readonly", width=16,
                                     values=("FCFS", "Round Robin", "Priority"))
        self.selector.pack(side="left", padx=7)
        self.selector.bind("<<ComboboxSelected>>", self._algorithm_changed)
        ttk.Label(controls, text="Time slice").pack(side="left", padx=(8, 0))
        self.quantum_box = ttk.Spinbox(controls, from_=1, to=20, textvariable=self.quantum, width=5)
        self.quantum_box.pack(side="left", padx=7)
        ttk.Button(controls, text="Show results", command=self.run_simulation).pack(side="left", padx=6)
        ttk.Label(controls, text="For Priority: smaller number goes first", style="Muted.TLabel").pack(side="right")

        self.metrics = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"))
        self.metrics.pack(anchor="w", pady=(2, 8))
        cols = ("pid", "user", "request", "arrival", "burst", "priority", "start", "completion", "wait", "turnaround")
        self.table = ttk.Treeview(self, columns=cols, show="headings", height=8)
        labels = ("ID", "User", "Request", "Arrives", "CPU time", "Priority", "First run", "Finished", "Wait", "Total time")
        widths = (50, 80, 175, 65, 60, 70, 85, 80, 60, 85)
        for col, label, width in zip(cols, labels, widths):
            self.table.heading(col, text=label)
            self.table.column(col, width=width, anchor="w" if col == "request" else "center")
        self.table.pack(fill="x", pady=(0, 10))

        ttk.Label(self, text="Which request uses the CPU, and when", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.canvas = tk.Canvas(self, height=58, bg="white", highlightthickness=1, highlightbackground="#d8dee5")
        self.canvas.pack(fill="x")
        ttk.Label(self, text="Request steps (New = created, Ready = waiting, Running = using CPU, Terminated = finished)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 4))
        self.states = tk.Text(self, height=5, wrap="word", font=("Consolas", 9), bg="white", relief="flat",
                              padx=9, pady=6, state="disabled")
        self.states.pack(fill="x")

    @staticmethod
    def _system_summary() -> str:
        return (f"This app's process ID: {os.getpid()}     CPU cores: {os.cpu_count() or 'unknown'}\n"
                f"Computer: {platform.system()} {platform.release()}     Python version: {platform.python_version()}")

    def _algorithm_changed(self, _event=None) -> None:
        self.quantum_box.configure(state="normal" if self.algorithm.get() == "Round Robin" else "disabled")

    def load_recent_actions(self) -> None:
        recent = [op for op in reversed(self.db.recent_operations(20)) if op["status"] == "Completed"][-5:]
        if not recent:
            messagebox.showinfo("No actions yet", "Add a student or save a course record first. Then load your recent actions here.")
            return
        jobs = []
        for i, operation in enumerate(recent):
            action = operation["action"]
            priority = 0 if "export" in action.lower() else (1 if "student" in action.lower() else 2)
            estimated_cpu = 2 + (len(action) % 4)
            jobs.append(Request(f"A{i + 1}", "CampusDesk", action, i, estimated_cpu, priority))
        self.requests = jobs
        self.workload_note.configure(text=f"Replaying {len(jobs)} recent actions. CPU times and priorities are estimates.")
        self.run_simulation()

    def run_background_task(self) -> None:
        self.thread_button.configure(state="disabled")
        self.thread_result.configure(text="Loading student profiles…")

        def worker() -> None:
            students = self.db.list_students()
            worker_id = threading.get_ident()
            self.after(0, lambda: self._finish_background_task(len(students), worker_id))

        threading.Thread(target=worker, name="sis-demo-worker", daemon=True).start()

    def _finish_background_task(self, count: int, worker_id: int) -> None:
        self.thread_button.configure(state="normal")
        self.thread_result.configure(text=f"Loaded {count} students (worker thread {worker_id})")

    def run_simulation(self) -> None:
        try:
            result = simulate(self.requests, self.algorithm.get(), int(self.quantum.get()))
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Invalid setting", str(exc))
            return
        self._show_result(result)

    def _show_result(self, result: SimulationResult) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for r in result.requests:
            self.table.insert("", "end", values=(r.pid, r.user, r.kind, r.arrival, r.burst, r.priority,
                r.first_start, r.completion, SimulationResult.wait_time(r), SimulationResult.turnaround_time(r)))
        suffix = f" · quantum {self.quantum.get()}" if result.algorithm == "Round Robin" else ""
        self.metrics.configure(text=f"{result.algorithm}{suffix}     Average waiting: {result.average_wait:.2f}     Average total time: {result.average_turnaround:.2f}")
        self.states.configure(state="normal")
        self.states.delete("1.0", "end")
        for r in result.requests:
            self.states.insert("end", f"{r.pid}: {' → '.join(r.transitions)}\n")
        self.states.configure(state="disabled")
        self._draw_timeline(result)

    def _draw_timeline(self, result: SimulationResult) -> None:
        canvas = self.canvas
        canvas.delete("all")
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 400)
        total = max((end for _, end, _ in result.timeline), default=1)
        left, right = 25, width - 18
        palette = ("#dceaf7", "#dff0e5", "#fff0d6", "#eee5f5", "#f8e1e1")
        ids = sorted({pid for _, _, pid in result.timeline})
        colors = {pid: palette[i % len(palette)] for i, pid in enumerate(ids)}
        for start, end, pid in result.timeline:
            x1, x2 = left + (right-left)*start/total, left + (right-left)*end/total
            canvas.create_rectangle(x1, 5, x2, 38, fill=colors[pid], outline="#9aa8b5")
            if x2-x1 > 23:
                canvas.create_text((x1+x2)/2, 21, text=pid, font=("Segoe UI", 9, "bold"))
            canvas.create_text(x1, 48, text=str(start), anchor="n", font=("Segoe UI", 8))
        canvas.create_text(right, 48, text=str(total), anchor="n", font=("Segoe UI", 8))
