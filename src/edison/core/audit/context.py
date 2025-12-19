from __future__ import annotations

from dataclasses import dataclass
from contextvars import ContextVar
from typing import Optional, Sequence


@dataclass(frozen=True)
class AuditContext:
    invocation_id: str
    argv: Sequence[str]
    command_name: str
    session_id: Optional[str] = None


_AUDIT_CONTEXT: ContextVar[AuditContext | None] = ContextVar("_AUDIT_CONTEXT", default=None)


def get_audit_context() -> AuditContext | None:
    return _AUDIT_CONTEXT.get()


def set_audit_context(ctx: AuditContext) -> None:
    _AUDIT_CONTEXT.set(ctx)


def clear_audit_context() -> None:
    _AUDIT_CONTEXT.set(None)


__all__ = ["AuditContext", "get_audit_context", "set_audit_context", "clear_audit_context"]

