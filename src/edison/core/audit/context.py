from __future__ import annotations

from collections.abc import Sequence
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditContext:
    invocation_id: str
    argv: Sequence[str]
    command_name: str
    session_id: str | None = None
    task_id: str | None = None


_AUDIT_CONTEXT: ContextVar[AuditContext | None] = ContextVar("_AUDIT_CONTEXT", default=None)


def get_audit_context() -> AuditContext | None:
    return _AUDIT_CONTEXT.get()


def set_audit_context(ctx: AuditContext) -> None:
    _AUDIT_CONTEXT.set(ctx)


def clear_audit_context() -> None:
    _AUDIT_CONTEXT.set(None)


__all__ = ["AuditContext", "get_audit_context", "set_audit_context", "clear_audit_context"]
