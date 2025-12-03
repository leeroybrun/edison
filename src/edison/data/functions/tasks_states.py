"""
Utility functions available to the template engine via {{function:...}}.

Functions here are loaded by the layered functions loader:
- core functions (this file)
- pack functions (bundled packs/<pack>/functions)
- project pack functions (.edison/packs/<pack>/functions)
- project functions (.edison/functions)

All functions should be pure and return strings.
"""
from __future__ import annotations

from typing import List, Optional


TASK_STATES: List[str] = [
    "todo",
    "in-progress",
    "review",
    "blocked",
    "done",
]


def tasks_states(state: Optional[str] = None) -> str:
    """Return allowed task states or details for a specific state.

    Args:
        state: Optional state name. When provided, returns a single-line
            description. When omitted, returns a bullet list of all states.

    Returns:
        String formatted for markdown injection.
    """
    if state:
        normalized = state.strip().lower()
        if normalized not in TASK_STATES:
            return f"Unknown task state: {state}"
        return f"{normalized}: allowed transitions depend on project rules."

    return "\n".join(f"- {s}" for s in TASK_STATES)

