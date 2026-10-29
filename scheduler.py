"""Single-CPU scheduling algorithms for synthetic student service requests."""

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from models import Request


@dataclass
class SimulationResult:
    algorithm: str
    timeline: list[tuple[int, int, str]]
    requests: list[Request]

    @property
    def average_wait(self) -> float:
        return sum(self.wait_time(r) for r in self.requests) / len(self.requests) if self.requests else 0

    @property
    def average_turnaround(self) -> float:
        return sum(self.turnaround_time(r) for r in self.requests) / len(self.requests) if self.requests else 0

    @staticmethod
    def turnaround_time(request: Request) -> int:
        return (request.completion or 0) - request.arrival

    @classmethod
    def wait_time(cls, request: Request) -> int:
        return cls.turnaround_time(request) - request.burst


def simulate(source: Iterable[Request], algorithm: str, quantum: int = 2) -> SimulationResult:
    """Run FCFS, Round Robin, or non-preemptive Priority scheduling."""
    if algorithm not in {"FCFS", "Round Robin", "Priority"}:
        raise ValueError(f"Unsupported scheduling algorithm: {algorithm}")
    if quantum < 1:
        raise ValueError("Round Robin quantum must be at least 1.")

    jobs = sorted((r.fresh_copy() for r in source), key=lambda r: (r.arrival, r.pid))
    timeline: list[tuple[int, int, str]] = []
    ready: deque[Request] = deque()
    pending = deque(jobs)
    time = 0
    running: Request | None = None
    slice_used = 0

    while pending or ready or running:
        while pending and pending[0].arrival <= time:
            arrived = pending.popleft()
            arrived.change_state("Ready")
            ready.append(arrived)

        if running is None:
            if not ready:
                if pending:
                    time = max(time, pending[0].arrival)
                    continue
                break
            if algorithm == "Priority":
                running = min(ready, key=lambda r: (r.priority, r.arrival, r.pid))
                ready.remove(running)
            else:
                running = ready.popleft()
            running.change_state("Running")
            if running.first_start is None:
                running.first_start = time
            slice_used = 0

        if timeline and timeline[-1][2] == running.pid and timeline[-1][1] == time:
            start, _, pid = timeline[-1]
            timeline[-1] = (start, time + 1, pid)
        else:
            timeline.append((time, time + 1, running.pid))

        running.remaining -= 1
        time += 1
        slice_used += 1
        while pending and pending[0].arrival <= time:
            arrived = pending.popleft()
            arrived.change_state("Ready")
            ready.append(arrived)

        if running.remaining == 0:
            running.completion = time
            running.change_state("Terminated")
            running = None
        elif algorithm == "Round Robin" and slice_used == quantum:
            running.change_state("Ready")
            ready.append(running)
            running = None

    return SimulationResult(algorithm, timeline, jobs)
