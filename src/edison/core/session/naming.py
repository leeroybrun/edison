"""
Session naming based on process tree inspection.

Generates session IDs in format: {process-name}-pid-{pid}[-seq-{n}]

This module is intentionally simple - all the complexity is in
the process inspector module. We just delegate to it.

The sequence counter ensures uniqueness when multiple sessions
are created within the same process.

Examples:
  - edison-pid-12345 (First session in this process)
  - edison-pid-12345-seq-1 (Second session)
  - claude-pid-54321 (Manual Claude workflow)
"""

from __future__ import annotations

import os
import threading
from typing import List, Optional

from ..process import inspector

# Thread-safe counter for session uniqueness within the same process
_counter_lock = threading.Lock()
_session_counter: dict[int, int] = {}  # PID -> counter


def reset_session_naming_counter() -> None:
    """Reset the session naming counter.

    This is primarily for testing purposes to ensure clean test state.
    In production, the counter persists for the lifetime of the process.
    """
    global _session_counter
    with _counter_lock:
        _session_counter.clear()


def _get_next_sequence(pid: int) -> int:
    """Get the next sequence number for a given PID, thread-safely.

    Args:
        pid: Process ID to get sequence for

    Returns:
        Sequence number (0 for first call, incrementing thereafter)
    """
    with _counter_lock:
        current = _session_counter.get(pid, 0)
        _session_counter[pid] = current + 1
        return current


class SessionNamingError(Exception):
    """Raised when session naming fails."""





def generate_session_id() -> str:
    """
    Generate a session ID by inspecting the process tree.

    This function replaces the SessionNamingStrategy.generate() method.
    It infers the session ID from the process tree and appends a sequence number
    for uniqueness within the same process.

    Returns:
        PID-based session ID (e.g., "edison-pid-12345" or "edison-pid-12345-seq-1")
    """
    try:
        # Get base session ID from process tree
        process_name, pid = inspector.find_topmost_process()
        base_id = f"{process_name}-pid-{pid}"

        # Add sequence number for uniqueness within this process
        seq = _get_next_sequence(pid)
        if seq == 0:
            return base_id
        return f"{base_id}-seq-{seq}"
    except Exception as exc:  # pragma: no cover - defensive
        raise SessionNamingError(f"Failed to infer session ID: {exc}") from exc


__all__ = ["SessionNamingError", "reset_session_naming_counter", "generate_session_id"]

