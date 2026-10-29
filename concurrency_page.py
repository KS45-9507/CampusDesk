"""Interactive concurrency and deadlock demonstrations for the OS PBL."""

import queue
import json
import sqlite3
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from concurrency_tools import bankers_safe_sequence
from database import Database


class ConcurrencyPage(ttk.Frame):
    def __init__(self, parent, db: Database) -> None:
        super().__init__(parent, padding=18)
        self.db = db
        ttk.Label(self, text="Concurrency and deadlocks", style="Section.TLabel").pack(anchor="w")
        ttk.Label(self, text="See what can go wrong when tasks share data, and how operating systems coordinate them.",
                  style="Muted.TLabel").pack(anchor="w", pady=(3, 12))
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self._build_operations_tab()
        self._build_race_tab()
        self._build_buffer_tab()
        self._build_banker_tab()
        self._build_ipc_tab()
        self._build_database_tab()
        self._build_concepts_tab()

    def _build_operations_tab(self) -> None:
        frame = self._new_tab("Your SIS actions")
        ttk.Label(frame, text="These are real actions you perform in CampusDesk, such as adding a student or saving marks.",
                  wraplength=850).pack(anchor="w", pady=(0, 4))
        ttk.Label(frame, text="Adding students, saving marks, editing, deleting, exporting, and backing up create real entries here. Saves use worker threads, one shared database lock, and a database transaction. The operation steps are an OS learning trace; the operating system still chooses the actual CPU order.",
                  wraplength=850, style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        columns = ("id", "action", "status", "process", "time")
        self.operations_table = ttk.Treeview(frame, columns=columns, show="headings", height=9)
        for col, title, width in (("id", "Action #", 65), ("action", "What you did", 210),
                                  ("status", "Result", 95), ("process", "App process", 100), ("time", "Started", 180)):
            self.operations_table.heading(col, text=title)
            self.operations_table.column(col, width=width, anchor="w" if col == "action" else "center")
        self.operations_table.pack(fill="x", pady=(0, 10))
        self.operations_table.bind("<<TreeviewSelect>>", self._show_operation)
        ttk.Label(frame, text="Steps for the selected action", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.operation_details = tk.Text(frame, height=8, wrap="word", font=("Consolas", 9), bg="white", relief="flat", padx=9, pady=7)
        self.operation_details.pack(fill="both", expand=True)
        self.operation_details.configure(state="disabled")
        self.refresh_operations()

    def refresh_operations(self) -> None:
        if not hasattr(self, "operations_table"):
            return
        for item in self.operations_table.get_children():
            self.operations_table.delete(item)
        for operation in self.db.recent_operations():
            self.operations_table.insert("", "end", values=(operation["operation_id"], operation["action"],
                operation["status"], operation["os_pid"], operation["started_at"].replace("T", " ")))
        if hasattr(self, "ipc_student_box"):
            choices = self.db.list_student_choices()
            self.ipc_student_map = {f"{sid} — {name}": sid for sid, name in choices}
            self.ipc_student_box["values"] = list(self.ipc_student_map)
            if self.ipc_student.get() not in self.ipc_student_map:
                self.ipc_student.set(next(iter(self.ipc_student_map), ""))
        if hasattr(self, "transaction_record_box"):
            self._refresh_transaction_records()

    def _show_operation(self, _event=None) -> None:
        selected = self.operations_table.selection()
        if not selected:
            return
        operation_id = int(self.operations_table.item(selected[0], "values")[0])
        operation = next((item for item in self.db.recent_operations(1000) if item["operation_id"] == operation_id), None)
        events = self.db.operation_events(operation_id)
        lines = []
        if operation:
            lines.append(f"Action: {operation['action']} — {operation['details']}")
            lines.append(f"App process ID: {operation['os_pid']}    Worker thread ID: {operation['thread_id']}")
        lines.extend(f"{event['state']}: {event['details']}" for event in events)
        self.operation_details.configure(state="normal")
        self.operation_details.delete("1.0", "end")
        self.operation_details.insert("end", "\n".join(lines))
        self.operation_details.configure(state="disabled")

    def _new_tab(self, title: str) -> ttk.Frame:
        frame = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(frame, text=title)
        return frame

    def _build_race_tab(self) -> None:
        frame = self._new_tab("Race and locks")
        ttk.Label(frame, text="When two staff members save attendance for the same student, both updates must be protected. These buttons show the lost-update problem safely; the real student and marks screens use a shared database lock.",
                  wraplength=850).pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(frame); row.pack(anchor="w")
        self.race_buttons = []
        for label, locked in (("Run without a lock", False), ("Run with a lock", True)):
            button = ttk.Button(row, text=label, command=lambda safe=locked: self._run_race(safe))
            button.pack(side="left", padx=(0, 8)); self.race_buttons.append(button)
        self.race_result = ttk.Label(frame, text="The expected total is 2. Compare both runs.", font=("Segoe UI", 11, "bold"))
        self.race_result.pack(anchor="w", pady=14)
        ttk.Label(frame, text="A critical section is the small piece of code that reads and updates shared data. A mutex lock lets only one task enter it at a time.",
                  wraplength=850, style="Muted.TLabel").pack(anchor="w")

    def _run_race(self, safe: bool) -> None:
        for button in self.race_buttons: button.configure(state="disabled")
        self.race_result.configure(text="Running two worker threads…")

        def work() -> None:
            shared = [0]
            lock = threading.Lock()
            both_read = threading.Barrier(2)

            def add_one() -> None:
                if safe:
                    with lock:
                        value = shared[0]
                        time.sleep(0.03)
                        shared[0] = value + 1
                else:
                    value = shared[0]
                    both_read.wait()
                    shared[0] = value + 1

            workers = [threading.Thread(target=add_one) for _ in range(2)]
            for worker in workers: worker.start()
            for worker in workers: worker.join()
            self.after(0, lambda: self._show_race_result(shared[0], safe))

        threading.Thread(target=work, name="race-demo", daemon=True).start()

    def _show_race_result(self, value: int, safe: bool) -> None:
        for button in self.race_buttons: button.configure(state="normal")
        if safe:
            text = f"With a lock: total = {value}. Both updates were kept."
        else:
            text = f"Without a lock: total = {value}. Both tasks read the old value, so one update was lost."
        self.race_result.configure(text=text)

    def _build_buffer_tab(self) -> None:
        frame = self._new_tab("Producer and consumer")
        ttk.Label(frame, text="Student forms, marks, and report requests arrive for processing. A producer places requests in a buffer; a consumer handles them. The buffer holds at most three.",
                  wraplength=850).pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text="Start both workers to place recent actions (Add student, Save marks, Export report) in a bounded queue. This replays their names only; it does not repeat or change your records.",
                  wraplength=850, style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        self.buffer_button = ttk.Button(frame, text="Start producer and consumer", command=self._start_buffer)
        self.buffer_button.pack(anchor="w")
        self.buffer_view = tk.Text(frame, height=15, wrap="word", font=("Consolas", 10), bg="white", relief="flat", padx=10, pady=8)
        self.buffer_view.pack(fill="both", expand=True, pady=(10, 0))
        self.buffer_view.insert("end", "Buffer is empty.\n")
        self.buffer_view.configure(state="disabled")

    def _start_buffer(self) -> None:
        self.buffer_button.configure(state="disabled")
        self.buffer_view.configure(state="normal"); self.buffer_view.delete("1.0", "end")
        self.buffer_view.configure(state="disabled")
        shared_queue: queue.Queue[str] = queue.Queue(maxsize=3)
        recent = [op for op in reversed(self.db.recent_operations(20)) if op["status"] == "Completed"][-5:]
        items = [f"{op['action']} (#{op['operation_id']})" for op in recent]
        if not items:
            items = ["Add student", "Save marks", "Update attendance", "Export report", "Back up database"]
        completion_lock = threading.Lock()
        remaining = [2]

        def log(message: str) -> None:
            self.after(0, lambda: self._append_buffer(message))

        def finished() -> None:
            with completion_lock:
                remaining[0] -= 1
                done = remaining[0] == 0
            if done:
                self.after(0, lambda: self.buffer_button.configure(state="normal"))

        def produce() -> None:
            for item in items:
                shared_queue.put(item)
                log(f"Producer added {item}  |  buffer has {shared_queue.qsize()} / 3\n")
                time.sleep(0.22)
            finished()

        def consume() -> None:
            for _ in range(len(items)):
                item = shared_queue.get()
                log(f"Consumer handled {item}  |  buffer has {shared_queue.qsize()} / 3\n")
                shared_queue.task_done()
                time.sleep(0.38)
            finished()

        threading.Thread(target=produce, name="producer", daemon=True).start()
        threading.Thread(target=consume, name="consumer", daemon=True).start()

    def _append_buffer(self, message: str) -> None:
        self.buffer_view.configure(state="normal")
        self.buffer_view.insert("end", message)
        self.buffer_view.see("end")
        self.buffer_view.configure(state="disabled")

    def _build_banker_tab(self) -> None:
        frame = self._new_tab("Avoid deadlock")
        ttk.Label(frame, text="Banker’s algorithm checks whether giving database access, a student-record lock, and an export-file slot still lets every CampusDesk task finish.",
                  wraplength=850).pack(anchor="w", pady=(0, 10))
        ttk.Button(frame, text="Check the example", command=self._run_banker).pack(anchor="w")
        self.banker_result = tk.Text(frame, height=10, wrap="word", font=("Consolas", 10), bg="white", relief="flat", padx=10, pady=8)
        self.banker_result.pack(fill="x", pady=10)
        explanation = ("This example uses three shared resources and five CampusDesk actions. The Available counts show what can still be assigned. "
                       "A safe order means each process can finish and return its resources. Avoidance checks a request before granting it; "
                       "detection checks an already-running system for a deadlock.")
        ttk.Label(frame, text=explanation, wraplength=850, style="Muted.TLabel").pack(anchor="w")
        self._run_banker()

    def _run_banker(self) -> None:
        allocation = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
        maximum = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
        available = [3, 3, 2]
        sequence = bankers_safe_sequence(allocation, maximum, available)
        names = ("Add student", "Save marks", "Update attendance", "Export course report", "Back up database")
        text = "Illustrative resources: DB connections = 3, record locks = 3, export slots = 2\n"
        text += "Safe order: " + (" → ".join(f"P{i} ({names[i]})" for i in sequence) if sequence else "No safe order; the state is unsafe.")
        self.banker_result.delete("1.0", "end"); self.banker_result.insert("end", text)

    def _build_ipc_tab(self) -> None:
        frame = self._new_tab("Process messages")
        ttk.Label(frame, text="Choose a student to create a short course summary. CampusDesk sends the selected details to a child process through a pipe.",
                  wraplength=850).pack(anchor="w", pady=(0, 10))
        row = ttk.Frame(frame); row.pack(fill="x")
        self.ipc_student = tk.StringVar()
        self.ipc_student_box = ttk.Combobox(row, textvariable=self.ipc_student, state="readonly", width=42)
        self.ipc_student_box.pack(side="left", fill="x", expand=True)
        self.ipc_button = ttk.Button(row, text="Send course summary", command=self._send_process_message)
        self.ipc_button.pack(side="left", padx=(8, 0))
        self.ipc_result = ttk.Label(frame, text="The child process reply will appear here.", wraplength=850)
        self.ipc_result.pack(anchor="w", pady=14)

    def _send_process_message(self) -> None:
        student_id = getattr(self, "ipc_student_map", {}).get(self.ipc_student.get())
        if not student_id:
            messagebox.showinfo("Choose a student", "Add or choose a student before creating a course summary.")
            return
        student = self.db.get_student(student_id)
        records = [r for r in self.db.list_records(student_id) if r["student_id"] == student_id]
        payload = {"student_id": student["student_id"], "name": student["full_name"],
                   "program": student["program"], "semester": student["semester"],
                   "courses": [{"code": r["course_code"], "name": r["course_name"], "term": r["term"],
                                "marks": r["marks"], "attendance": r["attendance"]} for r in records]}
        self.ipc_button.configure(state="disabled")
        self.ipc_result.configure(text="Starting child process…")

        def worker() -> None:
            code = ("import os,sys,json; d=json.load(sys.stdin); "
                    "print(f\"Child process {os.getpid()} prepared a summary for {d['name']} ({d['student_id']})\"); "
                    "[print(f\"{c['code']} {c['term']}: marks {c['marks']}%, attendance {c['attendance']}%\") for c in d['courses']] or print('No course records yet.')")
            try:
                result = subprocess.run([sys.executable, "-c", code], input=json.dumps(payload), capture_output=True,
                                        text=True, timeout=5, check=True)
                output = result.stdout.strip()
            except (subprocess.SubprocessError, OSError) as exc:
                output = f"Could not start the child process: {exc}"
            self.after(0, lambda: self._finish_ipc(output))

        threading.Thread(target=worker, name="ipc-demo", daemon=True).start()

    def _finish_ipc(self, output: str) -> None:
        self.ipc_button.configure(state="normal")
        self.ipc_result.configure(text=output)

    def _build_database_tab(self) -> None:
        frame = self._new_tab("Database transactions")
        ttk.Label(frame, text="A database transaction groups related changes. Either all changes are saved, or none are.",
                  wraplength=850).pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text="Choose a saved student course record. CampusDesk copies its mark into a temporary database, tries to update the mark and history together, then forces a failure to show rollback.",
                  wraplength=850, style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        self.transaction_record = tk.StringVar()
        self.transaction_record_box = ttk.Combobox(frame, textvariable=self.transaction_record, state="readonly", width=72)
        self.transaction_record_box.pack(anchor="w", pady=(0, 8))
        ttk.Button(frame, text="Show a failed save and rollback", command=self._transaction_demo).pack(anchor="w")
        self.transaction_result = ttk.Label(frame, text="The selected record is read only here. This demonstration does not change your project data.",
                                            wraplength=850)
        self.transaction_result.pack(anchor="w", pady=14)

    def _transaction_demo(self) -> None:
        record = getattr(self, "transaction_record_map", {}).get(self.transaction_record.get())
        if not record:
            messagebox.showinfo("Choose a course record", "Add or choose a saved course record first.")
            return
        con = sqlite3.connect(":memory:")
        con.executescript("CREATE TABLE marks (student TEXT, course TEXT, score REAL); CREATE TABLE activity (id INTEGER PRIMARY KEY, note TEXT);")
        con.execute("INSERT INTO marks VALUES (?, ?, ?)", (record["student_id"], record["course_code"], record["marks"]))
        con.execute("INSERT INTO activity VALUES (1, 'Existing activity')")
        con.commit()
        try:
            con.execute("BEGIN")
            con.execute("UPDATE marks SET score=? WHERE student=? AND course=?",
                        (min(100, record["marks"] + 5), record["student_id"], record["course_code"]))
            con.execute("INSERT INTO activity VALUES (1, 'This duplicate causes failure')")
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
        score = con.execute("SELECT score FROM marks").fetchone()[0]
        con.close()
        self.transaction_result.configure(text=f"For {record['student_id']} · {record['course_code']}, the history entry failed, so the mark update was undone. The saved mark remains {score:g}%. Your real course record was not changed.")

    def _refresh_transaction_records(self) -> None:
        records = self.db.list_records()
        labels = [f"{r['student_id']} — {r['full_name']} — {r['course_code']} ({r['term']})" for r in records]
        self.transaction_record_map = dict(zip(labels, records))
        self.transaction_record_box["values"] = labels
        if self.transaction_record.get() not in self.transaction_record_map:
            self.transaction_record.set(labels[0] if labels else "")

    def _build_concepts_tab(self) -> None:
        frame = self._new_tab("Other OS topics")
        topics = [
            ("Processes and race conditions", "A process is a running program; a thread is a task inside a program. Processes can run in the foreground or background, and can be independent or work together. Concurrency means tasks take turns over time; parallelism means they run at the same moment on different CPU cores. A race happens when the result depends on which task reaches shared data first."),
            ("Ways to coordinate", "A critical section is code that uses shared data. Strict alternation takes turns but can make a process wait when the other is idle. Peterson’s solution and Lamport’s Bakery algorithm are teaching methods for choosing one process at a time. Test-and-set is a hardware lock operation. A binary semaphore has two states; a counting semaphore tracks several available resources. A monitor groups shared data with safe operations."),
            ("Deadlock", "A deadlock can occur if one database operation holds a record lock while waiting for a file, and another holds the file while waiting for the database. A resource is exclusive, tasks hold resources while waiting, resources cannot be taken away, and the waits form a cycle. These are the four deadlock conditions."),
            ("Prevent, avoid, detect, recover", "Prevention breaks one of the four conditions. Avoidance checks whether a request keeps the system safe (Banker’s algorithm). Detection searches for a deadlock after it forms. Recovery can stop a task or take back and restore a resource."),
            ("Other classic examples", "Dining philosophers: coordinate shared forks without a circular wait. Readers and writers: allow safe reading together while protecting updates. Sleeping barber: use a limited waiting area for arriving customers. The producer–consumer tab demonstrates the bounded-buffer version."),
            ("Process communication", "Processes can exchange information through pipes, shared memory, message queues, or sockets. The process-messages tab demonstrates a pipe between this app and a child process."),
        ]
        for title, body in topics:
            section = ttk.LabelFrame(frame, text=title, padding=9)
            section.pack(fill="x", pady=5)
            ttk.Label(section, text=body, wraplength=850, justify="left").pack(anchor="w")
