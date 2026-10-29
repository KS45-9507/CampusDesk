"""Small, deterministic algorithms used by the concurrency learning area."""


def bankers_safe_sequence(allocation: list[list[int]], maximum: list[list[int]], available: list[int]) -> list[int] | None:
    """Return a safe process order, or None when the current state is unsafe."""
    if len(allocation) != len(maximum):
        raise ValueError("Allocation and maximum matrices must have the same number of processes.")
    if not allocation:
        return []
    resources = len(available)
    if any(len(row) != resources for row in allocation + maximum):
        raise ValueError("Every process row must have one value per resource type.")

    need = [[maximum[p][r] - allocation[p][r] for r in range(resources)]
            for p in range(len(allocation))]
    work = list(available)
    finished = [False] * len(allocation)
    order: list[int] = []

    while len(order) < len(allocation):
        found = False
        for p in range(len(allocation)):
            if not finished[p] and all(need[p][r] <= work[r] for r in range(resources)):
                work = [work[r] + allocation[p][r] for r in range(resources)]
                finished[p] = True
                order.append(p)
                found = True
        if not found:
            return None
    return order
