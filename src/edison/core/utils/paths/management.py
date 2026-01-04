"""Centralized project management paths resolution.

This module provides a low-level utility for computing paths relative to the
project management root directory (default: .project).

IMPORTANT DESIGN DECISION:
This class uses simple path computation ({management_root}/{subdirectory}).
It does NOT use domain configs (TaskConfig, SessionConfig) because:

1. Those configs read from bundled defaults, which always exist
2. This class needs to respect a custom management_dir without bundled defaults
3. The subdirectory names ("tasks", "qa", "sessions") are standard conventions

For explicit config-driven paths that may differ from management_root subdirs,
use the domain configs directly (TaskConfig.tasks_root(), QAConfig, etc.).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


class ProjectManagementPaths:
    """Resolve all project management directory paths from management root.
    
    This class computes paths as: {management_root}/{subdirectory_name}
    
    Use cases:
    - Tests that set custom management_dir and expect all subdirs to follow
    - Code that needs consistent path structure under management root
    
    For config-driven paths that may point elsewhere, use domain configs:
    - TaskConfig.tasks_root() - reads from tasks.paths.root
    - TaskConfig.qa_root() - reads from tasks.paths.qaRoot
    - SessionConfig.get_session_root_path() - reads from session.paths.root
    """

    def __init__(self, repo_root: Path, config: Optional[dict] = None):
        self.repo_root = repo_root
        self._config = config or self._load_config()

    # ----------------------- internal helpers ----------------------- #
    def _read_yaml(self, path: Path) -> Dict[str, Any]:
        from edison.core.utils.io import read_yaml

        data = read_yaml(path, default={})
        return data if isinstance(data, dict) else {}

    def _load_config(self) -> dict:
        """Load config to get management directory path.

        Resolution order:
        1) {config_dir}/config.yml
        2) {config_dir}/config.yaml
        3) {config_dir}/config/paths.yml
        4) {config_dir}/config/paths.yaml
        Falls back to defaults when none exist or contain a value.
        """
        from .project import get_project_config_dir

        config_dir = get_project_config_dir(self.repo_root)

        candidates = [
            config_dir / "config.yml",
            config_dir / "config.yaml",
            config_dir / "config" / "paths.yml",
            config_dir / "config" / "paths.yaml",
        ]

        merged: Dict[str, Any] = {}
        for path in candidates:
            data = self._read_yaml(path)
            if not data:
                continue
            merged.update(data)
            paths_block = data.get("paths")
            if isinstance(paths_block, dict):
                merged.update(paths_block)

        return merged

    # ----------------------- public API ----------------------- #
    def get_management_root(self) -> Path:
        """Get base management directory (default: .project)."""
        base = (
            self._config.get("project_management_dir")
            or self._config.get("management_dir")
            or self._config.get("paths", {}).get("management_dir")  # type: ignore[union-attr]
            or ".project"
        )
        return (self.repo_root / str(base)).resolve()

    def get_management_root_unresolved(self) -> Path:
        """Get the management directory path without resolving symlinks.

        This is primarily useful for user-facing output where we want paths like
        `.project/...` instead of a dereferenced worktree/meta path.
        """
        base = (
            self._config.get("project_management_dir")
            or self._config.get("management_dir")
            or self._config.get("paths", {}).get("management_dir")  # type: ignore[union-attr]
            or ".project"
        )
        return (self.repo_root / str(base)).expanduser()

    def get_tasks_root(self) -> Path:
        """Get tasks directory ({management_root}/tasks)."""
        return self.get_management_root() / "tasks"

    def get_task_state_dir(self, state: str) -> Path:
        """Get task state directory ({tasks_root}/{state})."""
        return self.get_tasks_root() / str(state)

    def get_sessions_root(self) -> Path:
        """Get sessions directory ({management_root}/sessions)."""
        return self.get_management_root() / "sessions"

    def get_session_state_dir(self, state: str) -> Path:
        """Get session state directory ({sessions_root}/{state})."""
        return self.get_sessions_root() / str(state)

    def get_qa_root(self) -> Path:
        """Get QA directory ({management_root}/qa)."""
        return self.get_management_root() / "qa"

    def get_logs_root(self) -> Path:
        """Get logs directory ({management_root}/logs)."""
        return self.get_management_root() / "logs"

    def get_archive_root(self) -> Path:
        """Get archive directory ({management_root}/archive)."""
        return self.get_management_root() / "archive"


# Global singleton for convenience
_paths_instance: Optional[ProjectManagementPaths] = None


def get_management_paths(repo_root: Optional[Path] = None) -> ProjectManagementPaths:
    """Get global ProjectManagementPaths instance."""
    global _paths_instance
    if _paths_instance is None or repo_root is not None:
        from .resolver import resolve_project_root

        root = repo_root or resolve_project_root()
        _paths_instance = ProjectManagementPaths(root)
    return _paths_instance


__all__ = ["ProjectManagementPaths", "get_management_paths"]



