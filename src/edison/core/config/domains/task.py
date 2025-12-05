"""Domain-specific configuration for tasks.

Provides cached access to task configuration including paths, state machine,
and default prefixes. Follows the same pattern as SessionConfig and QAConfig.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List

from ..base import BaseDomainConfig


class TaskConfig(BaseDomainConfig):
    """Provides access to task configuration (paths, states, defaults).

    Loads from bundled defaults (edison.data) with project overrides (.edison/config/).
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Note: This config also provides QA configuration access since tasks and QA
    are tightly coupled (each task has an associated QA record).
    """

    def _config_section(self) -> str:
        return "tasks"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def tasks_root(self) -> Path:
        """Get absolute path to tasks root directory."""
        path = self._paths.get("root")
        return self._resolve_required(path, "tasks.paths.root")

    def qa_root(self) -> Path:
        """Get absolute path to QA records root directory."""
        path = self._paths.get("qaRoot")
        return self._resolve_required(path, "tasks.paths.qaRoot")

    def meta_root(self) -> Path:
        """Get absolute path to metadata root directory."""
        path = self._paths.get("metaRoot")
        return self._resolve_required(path, "tasks.paths.metaRoot")

    def template_path(self) -> Path:
        """Get absolute path to task template file."""
        path = self._paths.get("template")
        return self._resolve_required(path, "tasks.paths.template")

    @cached_property
    def _paths(self) -> Dict[str, str]:
        """Get paths configuration section."""
        return dict(self.section.get("paths", {}) or {})

    def _resolve_required(self, rel: Any, key: str) -> Path:
        """Resolve a relative path to absolute, raising if missing."""
        if not rel:
            raise ValueError(f"Missing configuration: {key}")
        return (self.repo_root / str(rel)).resolve()

    # ------------------------------------------------------------------
    # State machine access
    # ------------------------------------------------------------------
    @cached_property
    def _state_machine(self) -> Dict[str, Dict]:
        """Get the statemachine configuration section.
        
        State machine config is under workflow.statemachine in the merged config.
        """
        workflow_section = self._config.get("workflow", {}) or {}
        return dict(workflow_section.get("statemachine", {}) or {})

    def task_states(self) -> List[str]:
        """Get list of valid task states from configuration."""
        states = self._state_machine.get("task", {}).get("states", {}) or {}
        if isinstance(states, dict):
            return list(states.keys())
        return list(states)

    def qa_states(self) -> List[str]:
        """Get list of valid QA states from configuration."""
        states = self._state_machine.get("qa", {}).get("states", {}) or {}
        if isinstance(states, dict):
            return list(states.keys())
        return list(states)

    def transitions(self, entity: str) -> Dict[str, List[str]]:
        """Get transition map for an entity type (task or qa).

        Args:
            entity: Entity type ("task" or "qa")

        Returns:
            Dict mapping from_state to list of allowed to_states
        """
        from edison.core.state import _flatten_transitions

        ent = self._state_machine.get(entity, {})
        states = ent.get("states", {}) or {}
        if isinstance(states, dict):
            return _flatten_transitions(states)
        transitions = ent.get("transitions", {}) or {}
        return {k: list(v or []) for k, v in transitions.items()}

    # ------------------------------------------------------------------
    # Defaults / prefixes
    # ------------------------------------------------------------------
    @cached_property
    def _defaults(self) -> Dict[str, str]:
        """Get defaults configuration section."""
        return dict(self.section.get("defaults", {}) or {})

    def defaults(self) -> Dict[str, str]:
        """Get all task defaults."""
        return dict(self._defaults)

    def default_prefix(self, key: str) -> str:
        """Get a default prefix value (e.g., 'taskId', 'qaId').

        Args:
            key: The default key to retrieve

        Returns:
            The configured prefix value

        Raises:
            ValueError: If the key is not configured
        """
        val = self._defaults.get(key)
        if val is None:
            raise ValueError(f"Missing configuration: tasks.defaults.{key}")
        return str(val)


__all__ = ["TaskConfig"]
