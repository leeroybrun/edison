from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from edison.core.audit.context import AuditContext, clear_audit_context, set_audit_context
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
    session_id: str | None,
    task_id: str | None,
) -> Iterator[InvocationAudit | None]:
    """Emit invocation start/end events and optionally tee stdio (fail-open)."""
    try:
        cfg = LoggingConfig(repo_root=repo_root)
    except Exception:
        cfg = None

    if cfg is None or not cfg.enabled:
        yield None
        return

    invocation_id = cfg.new_invocation_id()
    inv = InvocationAudit(invocation_id=invocation_id)
    should_emit_audit = bool(cfg.audit_enabled and cfg.audit_jsonl_enabled)
    tokens = cfg.build_tokens(invocation_id=invocation_id, session_id=session_id, project_root=repo_root)

    stdout_path, stderr_path = cfg.resolve_stdio_paths(tokens=tokens)
    stdlib_log_path = cfg.resolve_stdlib_log_path(tokens=tokens)

    def _redact_for_file(s: str) -> str:
        try:
            return cfg.redact_text(s)
        except Exception:
            return s

    if should_emit_audit:
        set_audit_context(
            AuditContext(
                invocation_id=invocation_id,
                argv=list(argv),
                command_name=command_name,
                session_id=session_id,
                task_id=task_id,
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

    if should_emit_audit:
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

    def _read_text_tail(path: Path, *, max_bytes: int) -> str:
        if max_bytes <= 0:
            return ""
        try:
            with path.open("rb") as fh:
                try:
                    size = fh.seek(0, os.SEEK_END)
                except Exception:
                    size = 0
                start = max(0, int(size) - int(max_bytes))
                try:
                    fh.seek(start, os.SEEK_SET)
                except Exception:
                    pass
                data = fh.read()
            return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

    with cm:
        yield inv

    # Emit end event only after stdio capture has flushed/closed its tee files.
    if should_emit_audit:
        payload: dict[str, object] = {
            "argv": list(argv),
            "command": command_name,
            "invocation_id": invocation_id,
            "exit_code": inv.exit_code,
            "duration_ms": (perf_counter() - t0) * 1000.0,
        }

        if cfg.invocation_embed_tails_enabled:
            max_bytes = int(cfg.invocation_embed_tails_max_bytes)
            if stdout_path is not None:
                stdout_tail = _read_text_tail(stdout_path, max_bytes=max_bytes)
                if stdout_tail:
                    payload["stdout_tail"] = (
                        cfg.redact_text(stdout_tail) if cfg.redaction_enabled else stdout_tail
                    )
            if stderr_path is not None:
                stderr_tail = _read_text_tail(stderr_path, max_bytes=max_bytes)
                if stderr_tail:
                    payload["stderr_tail"] = (
                        cfg.redact_text(stderr_tail) if cfg.redaction_enabled else stderr_tail
                    )
            if stdlib_log_path is not None:
                py_tail = _read_text_tail(stdlib_log_path, max_bytes=max_bytes)
                if py_tail:
                    payload["python_log_tail"] = (
                        cfg.redact_text(py_tail) if cfg.redaction_enabled else py_tail
                    )

        try:
            audit_event("cli.invocation.end", repo_root=repo_root, **payload)
        except Exception:
            pass
        finally:
            clear_audit_context()


@dataclass
class InvocationAudit:
    invocation_id: str
    exit_code: int | None = None

    def set_exit_code(self, code: int) -> None:
        self.exit_code = int(code)


__all__ = ["audit_invocation", "InvocationAudit"]
