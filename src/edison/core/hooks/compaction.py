"""Compaction event hooks.

Ensures constitutions are re-read after any context compaction by emitting
reminders and logging each compaction event. All behavior is driven entirely
from YAML configuration (compaction.hooks.*).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import ConfigManager
from ..file_io.utils import ensure_parent_dir
from ..utils.time import utc_timestamp
from ..paths import PathResolver
from ..paths.project import get_project_config_dir


class CompactionConfigError(ValueError):
    """Raised when compaction hook configuration is invalid or missing."""


@dataclass(frozen=True)
class CompactionHookSettings:
    """Normalized compaction hook settings resolved from YAML."""

    enabled: bool
    default_role: str
    default_source: str
    message_template: str
    notify: bool
    log_enabled: bool
    log_path: Path
    log_template: str

    @classmethod
    def from_config(cls, config: Dict[str, Any], *, repo_root: Path) -> "CompactionHookSettings":
        if not isinstance(config, dict) or not config:
            raise CompactionConfigError("compaction.hooks configuration is required")

        enabled = bool(config.get("enabled", True))

        default_role = config.get("defaultRole")
        if not isinstance(default_role, str) or not default_role.strip():
            raise CompactionConfigError("compaction.hooks.defaultRole must be configured")
        default_role = default_role.strip()

        default_source = config.get("defaultSource")
        if not isinstance(default_source, str) or not default_source.strip():
            raise CompactionConfigError("compaction.hooks.defaultSource must be configured")
        default_source = default_source.strip()

        reminder_cfg = config.get("reminder") or {}
        if not isinstance(reminder_cfg, dict):
            raise CompactionConfigError("compaction.hooks.reminder must be an object")

        message_template = reminder_cfg.get("messageTemplate")
        if not isinstance(message_template, str) or "{ROLE}" not in message_template:
            raise CompactionConfigError(
                "compaction.hooks.reminder.messageTemplate must contain the {ROLE} placeholder"
            )

        notify = bool(reminder_cfg.get("notify", True))

        log_cfg = config.get("log") or {}
        if not isinstance(log_cfg, dict):
            raise CompactionConfigError("compaction.hooks.log must be an object")

        log_enabled = bool(log_cfg.get("enabled", False))
        raw_log_path = log_cfg.get("path")
        log_template = log_cfg.get("entryTemplate")

        if log_enabled:
            if not isinstance(raw_log_path, str) or not raw_log_path.strip():
                raise CompactionConfigError("compaction.hooks.log.path is required when logging is enabled")
            if not isinstance(log_template, str) or not log_template.strip():
                raise CompactionConfigError("compaction.hooks.log.entryTemplate is required when logging is enabled")
        else:
            raw_log_path = raw_log_path if isinstance(raw_log_path, str) else ""
            log_template = log_template if isinstance(log_template, str) else ""

        resolved_log_path = _expand_path(raw_log_path, repo_root=repo_root) if raw_log_path else repo_root

        return cls(
            enabled=enabled,
            default_role=default_role,
            default_source=default_source,
            message_template=message_template,
            notify=notify,
            log_enabled=log_enabled,
            log_path=resolved_log_path,
            log_template=log_template,
        )


def _expand_path(raw: str, *, repo_root: Path) -> Path:
    project_dir = get_project_config_dir(repo_root)
    tokens = {
        "PROJECT_ROOT": str(repo_root),
        "PROJECT_DIR": str(project_dir),
        "PROJECT_CONFIG_DIR": str(project_dir),
        "PROJECT_CONFIG_BASENAME": project_dir.name,
    }

    try:
        expanded = raw.format(**tokens)
    except Exception:
        expanded = raw

    path = Path(expanded)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


class CompactionHook:
    """Triggerable hook for context compaction events."""

    def __init__(self, *, config: Optional[Dict[str, Any]] = None, repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else PathResolver.resolve_project_root()

        cfg_manager = ConfigManager(self.repo_root)
        full_config = config if config is not None else cfg_manager.load_config(validate=False)
        self.config = self._extract_config(full_config)
        self.settings = CompactionHookSettings.from_config(self.config, repo_root=self.repo_root)

    def trigger(self, *, role: Optional[str] = None, source: Optional[str] = None) -> str:
        """Trigger the compaction hook.

        Args:
            role: Role name used to substitute in the constitution reminder.
            source: Identifier for the compaction source (logged).

        Returns:
            Rendered reminder message (empty when hook disabled).
        """

        if not self.settings.enabled:
            return ""

        role_value = (role or self.settings.default_role).strip() or self.settings.default_role
        source_value = (source or self.settings.default_source).strip() or self.settings.default_source
        message = self.settings.message_template.replace("{ROLE}", role_value)

        if self.settings.notify:
            print(message)

        if self.settings.log_enabled:
            self._log_event(message=message, role=role_value, source=source_value)

        return message

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_config(self, full_config: Dict[str, Any]) -> Dict[str, Any]:
        compaction_cfg = full_config.get("compaction") if isinstance(full_config, dict) else {}
        if isinstance(compaction_cfg, dict):
            hooks_cfg = compaction_cfg.get("hooks")
            if isinstance(hooks_cfg, dict) and hooks_cfg:
                return hooks_cfg
            if compaction_cfg:
                return compaction_cfg
        raise CompactionConfigError("compaction.hooks section missing in configuration")

    def _log_event(self, *, message: str, role: str, source: str) -> None:
        tokens = {
            "timestamp": utc_timestamp(),
            "role": role,
            "source": source,
            "message": message,
        }

        try:
            line = self.settings.log_template.format(**tokens)
        except Exception as exc:
            raise CompactionConfigError(f"Invalid log entry template: {exc}") from exc

        ensure_parent_dir(self.settings.log_path)
        with self.settings.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(line.rstrip() + "\n")
