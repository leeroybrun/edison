from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterator, Optional, Sequence

from edison.core.audit.context import AuditContext, set_audit_context, clear_audit_context
from edison.core.audit.logger import audit_event
from edison.core.audit.stdio import capture_stdio
from edison.core.audit.stdlib_logging import configure_stdlib_logging
from edison.core.config.domains.logging import LoggingConfig


@contextmanager
def audit_invocation(
    *,
    argv: Sequence[str],
    command_name: str,
    repo_root: Path,
    session_id: Optional[str],
) -> Iterator["InvocationAudit | None"]:
    """Emit invocation start/end events and optionally tee stdio (fail-open)."""
    try:
        cfg = LoggingConfig(repo_root=repo_root)
    except Exception:
        cfg = None

    if cfg is None or not (cfg.enabled and cfg.audit_enabled):
        yield None
        return

    invocation_id = cfg.new_invocation_id()
    inv = InvocationAudit(invocation_id=invocation_id)
    tokens = cfg.build_tokens(invocation_id=invocation_id, session_id=session_id, project_root=repo_root)

    stdout_path, stderr_path = cfg.resolve_stdio_paths(tokens=tokens)
    stdlib_log_path = cfg.resolve_stdlib_log_path(tokens=tokens)

    def _redact_for_file(s: str) -> str:
        try:
            return cfg.redact_text(s)
        except Exception:
            return s

    set_audit_context(
        AuditContext(
            invocation_id=invocation_id,
            argv=list(argv),
            command_name=command_name,
            session_id=session_id,
        )
    )

    t0 = perf_counter()
    cm = (
        capture_stdio(
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            redact_for_file=_redact_for_file if cfg.redaction_enabled else None,
        )
        if cfg.stdio_capture_enabled
        else nullcontext()
    )

    if stdlib_log_path is not None:
        try:
            configure_stdlib_logging(log_path=stdlib_log_path, level=cfg.stdlib_level)
        except Exception:
            pass
    try:
        audit_event(
            "cli.invocation.start",
            repo_root=repo_root,
            argv=list(argv),
            command=command_name,
            invocation_id=invocation_id,
            stdout_path=str(stdout_path) if stdout_path else None,
            stderr_path=str(stderr_path) if stderr_path else None,
            stdlib_log_path=str(stdlib_log_path) if stdlib_log_path else None,
        )
    except Exception:
        pass

    with cm:
        try:
            yield inv
        finally:
            try:
                audit_event(
                    "cli.invocation.end",
                    repo_root=repo_root,
                    argv=list(argv),
                    command=command_name,
                    invocation_id=invocation_id,
                    exit_code=inv.exit_code,
                    duration_ms=(perf_counter() - t0) * 1000.0,
                )
            except Exception:
                pass
            clear_audit_context()


@dataclass
class InvocationAudit:
    invocation_id: str
    exit_code: Optional[int] = None

    def set_exit_code(self, code: int) -> None:
        self.exit_code = int(code)


__all__ = ["audit_invocation", "InvocationAudit"]
