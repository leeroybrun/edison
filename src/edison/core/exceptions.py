from __future__ import annotations

from typing import Any, Dict, Mapping


class EdisonError(Exception):
    """Base exception for Edison framework."""

    context: Dict[str, Any]

    def __init__(self, message: str = "", *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        if context is not None:
            # Store a shallow copy to avoid accidental mutation.
            self.context = dict(context)
        else:
            self.context = {}

    def to_json_error(self) -> Dict[str, Any]:
        """Return a JSON-serializable error payload."""
        return {
            "message": str(self),
            "code": self.__class__.__name__,
            "context": self.context,
        }


class SessionStateError(EdisonError, ValueError):
    """Raised when a session is in an invalid state."""

    def __init__(self, message: str = "", *, context: Mapping[str, Any] | None = None) -> None:
        EdisonError.__init__(self, message, context=context)
        ValueError.__init__(self, message)


class SessionNotFoundError(SessionStateError, FileNotFoundError):
    """Raised when a session record cannot be found."""


class TaskStateError(EdisonError, ValueError):
    """Raised when a task or QA record is in an invalid state."""

    def __init__(self, message: str = "", *, context: Mapping[str, Any] | None = None) -> None:
        EdisonError.__init__(self, message, context=context)
        ValueError.__init__(self, message)


class TaskNotFoundError(EdisonError, FileNotFoundError):
    """Raised when a task or QA record cannot be found."""

    def __init__(self, message: str = "", *, context: Mapping[str, Any] | None = None) -> None:
        EdisonError.__init__(self, message, context=context)
        FileNotFoundError.__init__(self, message)


class WorktreeError(EdisonError, RuntimeError):
    """Raised for errors in worktree creation, removal, or inspection."""

    def __init__(self, message: str = "", *, context: Mapping[str, Any] | None = None) -> None:
        EdisonError.__init__(self, message, context=context)
        RuntimeError.__init__(self, message)


class ValidationError(EdisonError):
    """Raised when validation of an artefact or API contract fails."""


class SessionError(EdisonError):
    """Generic session error."""

    def __init__(
        self,
        message: str,
        *,
        session_id: str | None = None,
        operation: str | None = None,
        details: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        ctx = dict(context or {})
        if session_id:
            ctx["session_id"] = session_id
        if operation:
            ctx["operation"] = operation
        if details:
            ctx["details"] = details
        super().__init__(message, context=ctx)


__all__ = [
    "EdisonError",
    "SessionError",
    "SessionStateError",
    "SessionNotFoundError",
    "TaskStateError",
    "TaskNotFoundError",
    "WorktreeError",
    "ValidationError",
]
