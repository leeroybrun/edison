"""Domain-specific configuration for Edison audit/logging.

This config controls:
- Whether Edison emits structured audit events
- Where project/session/invocation logs are stored
- Whether stdout/stderr are captured (tee) per CLI invocation
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ..base import BaseDomainConfig
from edison.core.utils.time import utc_timestamp


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover
        return "{" + key + "}"


@dataclass(frozen=True)
class LoggingPaths:
    project_audit_jsonl: str
    session_audit_jsonl: str
    invocation_dir: str
    invocation_audit_jsonl: str
    stdout_template: str
    stderr_template: str


class LoggingConfig(BaseDomainConfig):
    def _config_section(self) -> str:
        return "logging"

    @cached_property
    def enabled(self) -> bool:
        return bool(self.section.get("enabled", False))

    @cached_property
    def audit_enabled(self) -> bool:
        audit = self.section.get("audit") or {}
        return bool(audit.get("enabled", True))

    @cached_property
    def subprocess_enabled(self) -> bool:
        sub = self.section.get("subprocess") or {}
        return bool(sub.get("enabled", True))

    @cached_property
    def subprocess_max_output_bytes(self) -> int:
        sub = self.section.get("subprocess") or {}
        return int(sub.get("max_output_bytes", 0) or 0)

    @cached_property
    def stdio_capture_enabled(self) -> bool:
        stdio = self.section.get("stdio") or {}
        capture = stdio.get("capture") or {}
        return bool(capture.get("enabled", False))

    @cached_property
    def stdlib_enabled(self) -> bool:
        std = self.section.get("stdlib") or {}
        return bool(std.get("enabled", False))

    @cached_property
    def stdlib_level(self) -> str:
        std = self.section.get("stdlib") or {}
        return str(std.get("level", "INFO") or "INFO")

    @cached_property
    def stdlib_path_template(self) -> str:
        std = self.section.get("stdlib") or {}
        return str(std.get("path", "") or "")

    @cached_property
    def redaction_enabled(self) -> bool:
        red = self.section.get("redaction") or {}
        return bool(red.get("enabled", False))

    @cached_property
    def redaction_replacement(self) -> str:
        red = self.section.get("redaction") or {}
        return str(red.get("replacement", "[REDACTED]") or "[REDACTED]")

    @cached_property
    def redaction_patterns(self) -> list[str]:
        red = self.section.get("redaction") or {}
        pats = red.get("patterns") or []
        if not isinstance(pats, list):
            return []
        out: list[str] = []
        for p in pats:
            if p is None:
                continue
            s = str(p)
            if s.strip():
                out.append(s)
        return out

    @cached_property
    def _compiled_redaction_patterns(self) -> list[re.Pattern[str]]:
        if not (self.redaction_enabled and self.redaction_patterns):
            return []
        compiled: list[re.Pattern[str]] = []
        for pat in self.redaction_patterns:
            try:
                compiled.append(re.compile(pat))
            except Exception:
                continue
        return compiled

    def redact_text(self, text: str) -> str:
        if not (self.redaction_enabled and self._compiled_redaction_patterns):
            return text
        out = text
        for pat in self._compiled_redaction_patterns:
            out = pat.sub(self.redaction_replacement, out)
        return out

    def redact_payload(self, payload: Any) -> Any:
        if not (self.redaction_enabled and self._compiled_redaction_patterns):
            return payload
        if isinstance(payload, str):
            return self.redact_text(payload)
        if isinstance(payload, dict):
            return {k: self.redact_payload(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self.redact_payload(v) for v in payload]
        return payload

    @cached_property
    def orchestrator_enabled(self) -> bool:
        orch = self.section.get("orchestrator") or {}
        return bool(orch.get("enabled", True))

    @cached_property
    def orchestrator_capture_prompt(self) -> bool:
        orch = self.section.get("orchestrator") or {}
        return bool(orch.get("capture_prompt", False))

    @cached_property
    def orchestrator_max_prompt_bytes(self) -> int:
        orch = self.section.get("orchestrator") or {}
        return int(orch.get("max_prompt_bytes", 0) or 0)

    @cached_property
    def guards_enabled(self) -> bool:
        guards = self.section.get("guards") or {}
        return bool(guards.get("enabled", True))

    @cached_property
    def hooks_enabled(self) -> bool:
        hooks = self.section.get("hooks") or {}
        return bool(hooks.get("enabled", True))

    @cached_property
    def _jsonl_paths(self) -> Dict[str, Any]:
        audit = self.section.get("audit") or {}
        sinks = audit.get("sinks") or {}
        jsonl = sinks.get("jsonl") or {}
        paths = jsonl.get("paths") or {}
        return dict(paths) if isinstance(paths, dict) else {}

    @cached_property
    def paths(self) -> LoggingPaths:
        stdio = self.section.get("stdio") or {}
        capture = stdio.get("capture") or {}
        capture_paths = capture.get("paths") or {}
        if not isinstance(capture_paths, dict):
            capture_paths = {}

        return LoggingPaths(
            project_audit_jsonl=str(self._jsonl_paths.get("project") or ""),
            session_audit_jsonl=str(self._jsonl_paths.get("session") or ""),
            invocation_dir=str(self._jsonl_paths.get("invocation_dir") or ""),
            invocation_audit_jsonl=str(self._jsonl_paths.get("invocation") or ""),
            stdout_template=str(capture_paths.get("stdout") or ""),
            stderr_template=str(capture_paths.get("stderr") or ""),
        )

    def new_invocation_id(self) -> str:
        return uuid.uuid4().hex

    def build_tokens(
        self,
        *,
        invocation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        project_root: Optional[Path] = None,
    ) -> Dict[str, str]:
        effective_root = project_root if project_root is not None else self.repo_root
        tokens: Dict[str, Any] = {
            "invocation_id": invocation_id,
            "session_id": session_id,
            "project_root": str(project_root) if project_root is not None else str(self.repo_root),
            "pid": os.getpid(),
            "timestamp": utc_timestamp(repo_root=effective_root),
        }
        return {k: str(v) for k, v in tokens.items() if v is not None}

    def expand(self, template: str, tokens: Mapping[str, str]) -> str:
        return str(template).format_map(_SafeDict(tokens))

    def resolve_project_audit_path(self, *, tokens: Mapping[str, str]) -> Optional[Path]:
        if not self.paths.project_audit_jsonl:
            return None
        return (self.repo_root / self.expand(self.paths.project_audit_jsonl, tokens)).resolve()

    def resolve_session_audit_path(self, *, tokens: Mapping[str, str]) -> Optional[Path]:
        if not self.paths.session_audit_jsonl:
            return None
        if not tokens.get("session_id"):
            return None
        return (self.repo_root / self.expand(self.paths.session_audit_jsonl, tokens)).resolve()

    def resolve_invocation_audit_path(self, *, tokens: Mapping[str, str]) -> Optional[Path]:
        if not self.paths.invocation_audit_jsonl:
            return None
        if not tokens.get("invocation_id"):
            return None
        return (self.repo_root / self.expand(self.paths.invocation_audit_jsonl, tokens)).resolve()

    def resolve_stdio_paths(self, *, tokens: Mapping[str, str]) -> tuple[Optional[Path], Optional[Path]]:
        if not self.stdio_capture_enabled:
            return (None, None)
        out_t = self.paths.stdout_template
        err_t = self.paths.stderr_template
        if not out_t or not err_t:
            return (None, None)
        stdout_path = (self.repo_root / self.expand(out_t, tokens)).resolve()
        stderr_path = (self.repo_root / self.expand(err_t, tokens)).resolve()
        return (stdout_path, stderr_path)

    def resolve_stdlib_log_path(self, *, tokens: Mapping[str, str]) -> Optional[Path]:
        if not self.stdlib_enabled:
            return None
        if not self.stdlib_path_template:
            return None
        if not tokens.get("invocation_id"):
            return None
        return (self.repo_root / self.expand(self.stdlib_path_template, tokens)).resolve()


__all__ = ["LoggingConfig", "LoggingPaths"]
