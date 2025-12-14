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

    Pack overlays should not redefine task/workflow mechanics, but this domain
    still uses the unified config cache to avoid accidental double-loading.
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

    def evidence_subdir(self) -> str:
        """Get evidence subdirectory name from config.
        
        Returns the subdirectory name under qa_root where validation evidence
        is stored (default: "validation-evidence").
        """
        return self._paths.get("evidenceSubdir", "validation-evidence")

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
    # State machine access (delegates to WorkflowConfig for single source of truth)
    # ------------------------------------------------------------------
    @cached_property
    def _workflow_config(self) -> "WorkflowConfig":
        """Lazily load WorkflowConfig to avoid circular imports.
        
        WorkflowConfig is the single source of truth for state machine config.
        TaskConfig delegates to WorkflowConfig for all state-related queries.
        """
        from .workflow import WorkflowConfig
        return WorkflowConfig(repo_root=self.repo_root)

    def task_states(self) -> List[str]:
        """Get list of valid task states from configuration.
        
        Delegates to WorkflowConfig (single source of truth).
        """
        return self._workflow_config.task_states

    def qa_states(self) -> List[str]:
        """Get list of valid QA states from configuration.
        
        Delegates to WorkflowConfig (single source of truth).
        """
        return self._workflow_config.qa_states

    def transitions(self, entity: str) -> Dict[str, List[str]]:
        """Get transition map for an entity type (task or qa).

        Args:
            entity: Entity type ("task" or "qa")

        Returns:
            Dict mapping from_state to list of allowed to_states
            
        Delegates to WorkflowConfig (single source of truth).
        """
        return self._workflow_config.get_transitions(entity)

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
