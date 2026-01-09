from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from edison.core.audit.context import get_audit_context
from edison.core.audit.jsonl import append_jsonl
from edison.core.config.domains.logging import LoggingConfig
from edison.core.utils.time import utc_timestamp


def _best_effort_repo_root(repo_root: Path | None) -> Path | None:
    if repo_root is not None:
        try:
            return repo_root.expanduser().resolve()
        except Exception:
            return None
    try:
        from edison.core.utils.paths import PathResolver

        return PathResolver.resolve_project_root()
    except Exception:
        return None


def audit_event(event: str, *, repo_root: Path | None = None, **fields: Any) -> None:
    """Emit a single structured audit event as JSONL (fail-open).

    This is separate from stdlib `logging` so JSON-mode CLI output stays pure.
    """
    root = _best_effort_repo_root(repo_root)
    if root is None:
        return

    try:
        cfg = LoggingConfig(repo_root=root)
    except Exception:
        return

    if not cfg.enabled or not cfg.audit_enabled or not cfg.audit_jsonl_enabled:
        return

    # Category-level gating (kept centralized so emitters remain lightweight).
    try:
        if event.startswith("subprocess.") and not cfg.subprocess_enabled:
            return
        if event.startswith("orchestrator.") and not cfg.orchestrator_enabled:
            return
        if event.startswith("guard.") and not cfg.guards_enabled:
            return
        if event.startswith("hook.") and not cfg.hooks_enabled:
            return
    except Exception:
        # Fail open on config parsing edge cases.
        pass

    ctx = get_audit_context()
    ctx_invocation_id = ctx.invocation_id if ctx is not None else None
    ctx_session_id = ctx.session_id if ctx is not None else None
    ctx_task_id = ctx.task_id if ctx is not None else None

    # When a context exists, it is the canonical source of these ids.
    # Allow explicit ids only when there is no active context.
    invocation_id = ctx_invocation_id if ctx_invocation_id is not None else fields.get("invocation_id")
    session_id = ctx_session_id if ctx_session_id is not None else fields.get("session_id")
    task_id = ctx_task_id if ctx_task_id is not None else fields.get("task_id")

    tokens = cfg.build_tokens(
        invocation_id=invocation_id,
        session_id=session_id,
        project_root=root,
    )

    # Canonical audit log: a single append-only JSONL stream.
    path = cfg.resolve_project_audit_path(tokens=tokens)
    if path is None:
        return

    payload: dict[str, Any] = {
        "ts": utc_timestamp(repo_root=root),
        "event": event,
        "pid": os.getpid(),
        "invocation_id": invocation_id,
        "session_id": session_id,
        "task_id": task_id,
        "project_root": str(root),
    }

    # Prevent callers from overriding the canonical envelope fields.
    reserved = {"ts", "event", "pid", "project_root"}
    for k, v in fields.items():
        if k in reserved:
            continue
        if k in {"invocation_id", "session_id", "task_id"}:
            # Merged above with context taking precedence.
            continue
        payload[k] = v

    try:
        payload = cfg.redact_payload(payload)
    except Exception:
        pass

    append_jsonl(path=path, payload=payload, repo_root=root)


def truncate_text(text: str, *, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    raw = text.encode("utf-8", errors="replace")
    if len(raw) <= max_bytes:
        return text
    clipped = raw[:max_bytes]
    return clipped.decode("utf-8", errors="replace")


# -------------------------------------------------------------------------
# Tamper-evident logging for entity transitions
# -------------------------------------------------------------------------


def audit_entity_transition(
    entity_type: str,
    entity_id: str,
    from_state: str,
    to_state: str,
    *,
    repo_root: Path | None = None,
    session_id: str | None = None,
    reason: str | None = None,
) -> None:
    """Emit a tamper-evident audit event for an entity state transition.

    This function emits an `entity.transition` event to the canonical audit log,
    recording the old state, new state, entity type, and entity ID. This provides
    an immutable, append-only log of all state transitions for forensics.

    Args:
        entity_type: The type of entity (e.g., 'task', 'qa', 'session')
        entity_id: The unique identifier of the entity
        from_state: The previous state
        to_state: The new state
        repo_root: Optional repository root for config resolution
        session_id: Optional session ID for context
        reason: Optional reason for the transition
    """
    root = _best_effort_repo_root(repo_root)
    if root is None:
        return

    try:
        cfg = LoggingConfig(repo_root=root)
    except Exception:
        return

    if not cfg.enabled or not cfg.audit_enabled or not cfg.entity_transitions_enabled:
        return

    audit_event(
        "entity.transition",
        repo_root=root,
        entity_type=entity_type,
        entity_id=entity_id,
        from_state=from_state,
        to_state=to_state,
        session_id=session_id,
        reason=reason,
    )


def audit_evidence_write(
    task_id: str,
    artifact_type: str,
    path: str,
    round_num: int,
    *,
    repo_root: Path | None = None,
    validator_id: str | None = None,
) -> None:
    """Emit a tamper-evident audit event for an evidence write operation.

    This function emits an `evidence.write` event to the canonical audit log,
    recording the artifact type, file path, round number, and task ID. This provides
    an immutable, append-only log of all evidence writes for forensics.

    Args:
        task_id: The task ID this evidence belongs to
        artifact_type: Type of artifact (e.g., 'bundle', 'implementation_report', 'validator_report')
        path: The file path where evidence was written
        round_num: The validation round number
        repo_root: Optional repository root for config resolution
        validator_id: Optional validator ID for validator reports
    """
    root = _best_effort_repo_root(repo_root)
    if root is None:
        return

    try:
        cfg = LoggingConfig(repo_root=root)
    except Exception:
        return

    if not cfg.enabled or not cfg.audit_enabled or not cfg.evidence_writes_enabled:
        return

    audit_event(
        "evidence.write",
        repo_root=root,
        task_id=task_id,
        artifact_type=artifact_type,
        path=path,
        round=round_num,
        validator_id=validator_id,
    )


__all__ = [
    "audit_event",
    "truncate_text",
    "audit_entity_transition",
    "audit_evidence_write",
]
