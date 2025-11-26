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


class SessionNamingStrategy:
    """
    Session naming via process tree inspection.

    This class exists for backward compatibility with WAVE 1-4 code,
    but the implementation is now simple: just delegate to process inspector.

    Thread-safety: Multiple instances can safely generate IDs concurrently.
    Each call to generate() returns a unique ID via a thread-safe counter.
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize naming strategy.

        Args:
            config: Optional config dict (DEPRECATED - no longer used)

        Note:
            Config parameter kept for backward compatibility but ignored.
            Session naming is now always PID-based via process inspection.
        """
        # Config no longer used - naming is always PID-based
        self._config = config or {}

    @property
    def _current_pid(self) -> int:
        """Get the current process ID (for test compatibility)."""
        return os.getpid()

    def generate(
        self,
        process: Optional[str] = None,
        owner: Optional[str] = None,
        existing_sessions: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """
        Generate session ID by inspecting process tree.

        All parameters are DEPRECATED and ignored. Session ID is now
        inferred entirely from the process tree with a sequence suffix
        for uniqueness within the same process.

        Args:
            process: DEPRECATED - Ignored (kept for backward compatibility)
            owner: DEPRECATED - Ignored (kept for backward compatibility)
            existing_sessions: DEPRECATED - Ignored (no collision checking needed)
            **kwargs: DEPRECATED - All other args ignored

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

    def validate(self, session_id: str) -> bool:
        """
        Validate a session ID is legal.

        Args:
            session_id: Session ID to validate

        Returns:
            True if valid, False otherwise

        Note:
            This validation is lenient to support both PID-based (new)
            and legacy (old) session IDs.
        """
        if not session_id:
            return False

        if ".." in session_id or "/" in session_id or "\\" in session_id:
            return False

        return all(c.isalnum() or c in ["-", "_"] for c in session_id)


__all__ = ["SessionNamingStrategy", "SessionNamingError", "reset_session_naming_counter"]
