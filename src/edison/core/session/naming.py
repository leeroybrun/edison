"""
Session naming based on process tree inspection.

Generates session IDs in format: {process-name}-pid-{pid}

This module is intentionally simple - all the complexity is in
the process inspector module. We just delegate to it.

Examples:
  - edison-pid-12345 (Edison auto-start workflow)
  - claude-pid-54321 (Manual Claude workflow)
  - codex-pid-99999 (Manual Codex workflow)
"""

from __future__ import annotations

from typing import List, Optional

from ..process import inspector


class SessionNamingError(Exception):
    """Raised when session naming fails."""


class SessionNamingStrategy:
    """
    Session naming via process tree inspection.

    This class exists for backward compatibility with WAVE 1-4 code,
    but the implementation is now simple: just delegate to process inspector.
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
        inferred entirely from the process tree.

        Args:
            process: DEPRECATED - Ignored (kept for backward compatibility)
            owner: DEPRECATED - Ignored (kept for backward compatibility)
            existing_sessions: DEPRECATED - Ignored (no collision checking needed)
            **kwargs: DEPRECATED - All other args ignored

        Returns:
            PID-based session ID (e.g., "edison-pid-12345")
        """
        try:
            return inspector.infer_session_id()
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


__all__ = ["SessionNamingStrategy", "SessionNamingError"]
