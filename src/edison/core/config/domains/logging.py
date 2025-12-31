"""Domain-specific configuration for Edison audit/logging.

This config controls:
- Whether Edison emits structured audit events
- Where the canonical audit log is stored
- Whether stdout/stderr are captured (tee) per CLI invocation
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from edison.core.config.templating import SafeDict
from edison.core.utils.time import utc_timestamp

from ..base import BaseDomainConfig


@dataclass(frozen=True)
class LoggingPaths:
    audit_jsonl: str
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
    def audit_jsonl_enabled(self) -> bool:
        """Whether the canonical audit JSONL sink is enabled.

        New config (preferred):
          logging.audit.jsonl.enabled

        Legacy config (supported for compatibility):
          logging.audit.sinks.jsonl.enabled
        """
        audit = self.section.get("audit") or {}
        jsonl = audit.get("jsonl") or {}
        if isinstance(jsonl, dict) and "enabled" in jsonl:
            return bool(jsonl.get("enabled", True))

        sinks = audit.get("sinks") or {}
        jsonl2 = sinks.get("jsonl") or {}
        if isinstance(jsonl2, dict) and "enabled" in jsonl2:
            return bool(jsonl2.get("enabled", True))

        return True

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
    def _jsonl_paths(self) -> dict[str, Any]:
        audit = self.section.get("audit") or {}

        # New canonical config: a single audit JSONL path.
        #
        # This intentionally maps into the legacy "project" key so the rest of the
        # implementation can stay small and backward-compatible.
        raw_path = audit.get("path")
        if isinstance(raw_path, str) and raw_path.strip():
            return {"project": str(raw_path).strip()}

        sinks = audit.get("sinks") or {}
        jsonl = sinks.get("jsonl") or {}
        paths = jsonl.get("paths") or {}
        if not isinstance(paths, dict):
            return {}

        # Legacy support: only the "project" path is still meaningful now that
        # Edison uses a single canonical audit log stream.
        raw_legacy_project = paths.get("project")
        if isinstance(raw_legacy_project, str) and raw_legacy_project.strip():
            return {"project": str(raw_legacy_project).strip()}
        return {}

    @cached_property
    def invocation_embed_tails_enabled(self) -> bool:
        inv = self.section.get("invocation") or {}
        embed = inv.get("embed_tails") or {}
        return bool(isinstance(embed, dict) and embed.get("enabled", False))

    @cached_property
    def invocation_embed_tails_max_bytes(self) -> int:
        inv = self.section.get("invocation") or {}
        embed = inv.get("embed_tails") or {}
        if not isinstance(embed, dict):
            return 0
        try:
            return int(embed.get("max_bytes", 0) or 0)
        except Exception:
            return 0

    @cached_property
    def paths(self) -> LoggingPaths:
        stdio = self.section.get("stdio") or {}
        capture = stdio.get("capture") or {}
        capture_paths = capture.get("paths") or {}
        if not isinstance(capture_paths, dict):
            capture_paths = {}

        return LoggingPaths(
            audit_jsonl=str(self._jsonl_paths.get("project") or ""),
            stdout_template=str(capture_paths.get("stdout") or ""),
            stderr_template=str(capture_paths.get("stderr") or ""),
        )

    def new_invocation_id(self) -> str:
        return uuid.uuid4().hex

    def build_tokens(
        self,
        *,
        invocation_id: str | None = None,
        session_id: str | None = None,
        project_root: Path | None = None,
    ) -> dict[str, str]:
        effective_root = project_root if project_root is not None else self.repo_root
        tokens: dict[str, Any] = {
            "invocation_id": invocation_id,
            "session_id": session_id,
            "project_root": str(project_root) if project_root is not None else str(self.repo_root),
            "pid": os.getpid(),
            "timestamp": utc_timestamp(repo_root=effective_root),
        }
        out = {k: str(v) for k, v in tokens.items() if v is not None}
        return out

    def expand(self, template: str, tokens: Mapping[str, str]) -> str:
        return str(template).format_map(SafeDict(tokens))

    def resolve_project_audit_path(self, *, tokens: Mapping[str, str]) -> Path | None:
        if not self.paths.audit_jsonl:
            return None
        expanded = Path(self.expand(self.paths.audit_jsonl, tokens)).expanduser()
        if not expanded.is_absolute():
            expanded = self.repo_root / expanded
        return expanded.resolve()

    def resolve_stdio_paths(self, *, tokens: Mapping[str, str]) -> tuple[Path | None, Path | None]:
        if not self.stdio_capture_enabled:
            return (None, None)
        out_t = self.paths.stdout_template
        err_t = self.paths.stderr_template
        if not out_t or not err_t:
            return (None, None)
        stdout_path = Path(self.expand(out_t, tokens)).expanduser()
        if not stdout_path.is_absolute():
            stdout_path = self.repo_root / stdout_path
        stderr_path = Path(self.expand(err_t, tokens)).expanduser()
        if not stderr_path.is_absolute():
            stderr_path = self.repo_root / stderr_path
        return (stdout_path.resolve(), stderr_path.resolve())

    def resolve_stdlib_log_path(self, *, tokens: Mapping[str, str]) -> Path | None:
        if not self.stdlib_enabled:
            return None
        if not self.stdlib_path_template:
            return None
        if not tokens.get("invocation_id"):
            return None
        expanded = Path(self.expand(self.stdlib_path_template, tokens)).expanduser()
        if not expanded.is_absolute():
            expanded = self.repo_root / expanded
        return expanded.resolve()


__all__ = ["LoggingConfig", "LoggingPaths"]
