"""Configuration accessors for the task domain.

All task paths, prefixes, and state-machine values must originate from YAML
configuration loaded via :class:`lib.config.ConfigManager`. This module is a
thin façade to avoid hardcoded defaults and to keep the new task package
decoupled from the legacy ``task`` globals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..config import ConfigManager
from ..state import _flatten_transitions

# Fallbacks used only when configuration is incomplete. These retain previous
# behavior but keep values centralized for easier removal once all configs are
# present.
DEFAULT_PATHS = {
    "tasks.paths.root": ".project/tasks",
    "tasks.paths.qaRoot": ".project/qa",
    "tasks.paths.metaRoot": ".project/tasks/meta",
    "tasks.paths.template": ".project/tasks/TEMPLATE.md",
}

DEFAULT_PREFIXES = {
    "ownerPrefix": "- **Owner:** ",
    "validatorOwnerPrefix": "- **Validator Owner:** ",
    "statusPrefix": "- **Status:** ",
    "claimedPrefix": "  - **Claimed At:** ",
    "lastActivePrefix": "  - **Last Active:** ",
    "continuationPrefix": "  - **Continuation ID:** ",
}


class TaskConfig:
    """Typed access to task-related configuration.

    Args:
        repo_root: Optional repository root to anchor configuration loading.
            When omitted, :class:`ConfigManager` resolves the project root via
            :class:`PathResolver`, making the helper usable from CLI scripts
            and tests alike.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self._mgr = ConfigManager(repo_root=repo_root)
        self._config = self._mgr.load_config(validate=False)
        self.repo_root = self._mgr.repo_root

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def tasks_root(self) -> Path:
        path = self._paths().get("root")
        return self._resolve_required(path, "tasks.paths.root")

    def qa_root(self) -> Path:
        path = self._paths().get("qaRoot")
        return self._resolve_required(path, "tasks.paths.qaRoot")

    def meta_root(self) -> Path:
        path = self._paths().get("metaRoot")
        return self._resolve_required(path, "tasks.paths.metaRoot")

    def template_path(self) -> Path:
        path = self._paths().get("template")
        return self._resolve_required(path, "tasks.paths.template")

    def _paths(self) -> Dict[str, str]:
        return dict(self._config.get("tasks", {}).get("paths", {}) or {})

    def _resolve_required(self, rel: Optional[str], key: str) -> Path:
        if not rel:
            rel = DEFAULT_PATHS.get(key)
        if not rel:
            raise ValueError(f"Missing configuration: {key}")
        return (self.repo_root / rel).resolve()

    # ------------------------------------------------------------------
    # State machine access
    # ------------------------------------------------------------------
    def task_states(self) -> List[str]:
        states = self._state_machine().get("task", {}).get("states", {}) or {}
        if isinstance(states, dict):
            return list(states.keys())
        return list(states)

    def qa_states(self) -> List[str]:
        states = self._state_machine().get("qa", {}).get("states", {}) or {}
        if isinstance(states, dict):
            return list(states.keys())
        return list(states)

    def transitions(self, entity: str) -> Dict[str, List[str]]:
        ent = self._state_machine().get(entity, {})
        states = ent.get("states", {}) or {}
        if isinstance(states, dict):
            return _flatten_transitions(states)
        transitions = ent.get("transitions", {}) or {}
        return {k: list(v or []) for k, v in transitions.items()}

    def _state_machine(self) -> Dict[str, Dict]:
        return dict(self._config.get("statemachine", {}) or {})

    # ------------------------------------------------------------------
    # Defaults / prefixes
    # ------------------------------------------------------------------
    def defaults(self) -> Dict[str, str]:
        return dict(self._config.get("tasks", {}).get("defaults", {}) or {})

    def default_prefix(self, key: str) -> str:
        defaults = self.defaults()
        val = defaults.get(key)
        if val is None:
            val = DEFAULT_PREFIXES.get(key)
        if val is None:
            raise ValueError(f"Missing configuration: tasks.defaults.{key}")
        return str(val)


__all__ = ["TaskConfig"]
