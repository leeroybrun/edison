from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.audit.context import get_audit_context
from edison.core.audit.jsonl import append_jsonl
from edison.core.config.domains.logging import LoggingConfig
from edison.core.utils.time import utc_timestamp


def _best_effort_repo_root(repo_root: Optional[Path]) -> Optional[Path]:
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


def audit_event(event: str, *, repo_root: Optional[Path] = None, **fields: Any) -> None:
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

    if not cfg.enabled or not cfg.audit_enabled:
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
    invocation_id = ctx.invocation_id if ctx is not None else None
    session_id = ctx.session_id if ctx is not None else None

    tokens = cfg.build_tokens(
        invocation_id=invocation_id,
        session_id=session_id,
        project_root=root,
    )

    paths = [
        cfg.resolve_project_audit_path(tokens=tokens),
        cfg.resolve_session_audit_path(tokens=tokens),
        cfg.resolve_invocation_audit_path(tokens=tokens),
    ]
    # Avoid writing the same event twice to the same sink when templates resolve
    # to identical paths (e.g., project+session sinks configured to the same file).
    sink_paths: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        if p is None:
            continue
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        sink_paths.append(p)
    if not sink_paths:
        return

    payload: Dict[str, Any] = {
        "ts": utc_timestamp(repo_root=root),
        "event": event,
        "pid": os.getpid(),
        "invocation_id": invocation_id,
        "session_id": session_id,
        "project_root": str(root),
    }
    payload.update(fields)

    try:
        payload = cfg.redact_payload(payload)
    except Exception:
        pass

    for path in sink_paths:
        append_jsonl(path=path, payload=payload, repo_root=root)


def truncate_text(text: str, *, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    raw = text.encode("utf-8", errors="replace")
    if len(raw) <= max_bytes:
        return text
    clipped = raw[:max_bytes]
    return clipped.decode("utf-8", errors="replace")


__all__ = ["audit_event", "truncate_text"]
