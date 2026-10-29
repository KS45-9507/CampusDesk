"""Data models used by the student request scheduling simulator."""

from dataclasses import dataclass, field


@dataclass
class Request:
    """One synthetic university service request represented as a process."""

    pid: str
    user: str
    kind: str
    arrival: int
    burst: int
    priority: int
    remaining: int = field(init=False)
    first_start: int | None = None
    completion: int | None = None
    state: str = "New"
    transitions: list[str] = field(default_factory=lambda: ["New"])

    def __post_init__(self) -> None:
        if self.arrival < 0:
            raise ValueError("Arrival time cannot be negative.")
        if self.burst < 1:
            raise ValueError("Burst time must be at least 1.")
        if self.priority < 0:
            raise ValueError("Priority cannot be negative.")
        self.remaining = self.burst

    def change_state(self, state: str) -> None:
        if self.state != state:
            self.state = state
            self.transitions.append(state)

    def fresh_copy(self) -> "Request":
        """Return an unscheduled copy so each algorithm starts with clean state."""
        return Request(self.pid, self.user, self.kind, self.arrival, self.burst, self.priority)
