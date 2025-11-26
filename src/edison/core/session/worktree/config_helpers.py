"""Shared configuration helpers for worktree modules."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from edison.core.paths.resolver import PathResolver
from edison.core.session.config import SessionConfig
from edison.core.utils.project_config import (
    get_project_name,
    substitute_project_tokens,
)


def _config() -> SessionConfig:
    """Return a fresh SessionConfig bound to the current project root."""
    return SessionConfig(repo_root=PathResolver.resolve_project_root())


def _get_repo_dir() -> Path:
    return PathResolver.resolve_project_root()


def _get_project_name() -> str:
    """Resolve the active project name via ConfigManager."""
    return get_project_name()


def _worktree_base_dir(cfg: Dict[str, Any], repo_dir: Path) -> Path:
    base_dir_value = cfg.get("baseDirectory") or "../{PROJECT_NAME}-worktrees"
    substituted = substitute_project_tokens(str(base_dir_value), repo_dir)
    base_dir_path = Path(substituted)
    if base_dir_path.is_absolute():
        return base_dir_path
    anchor = repo_dir if (base_dir_path.parts and base_dir_path.parts[0] == "..") else repo_dir.parent
    return (anchor / base_dir_path).resolve()


def _resolve_worktree_target(session_id: str, cfg: Dict[str, Any]) -> tuple[Path, str]:
    """Compute worktree path and branch name from config and session id."""
    repo_dir = _get_repo_dir()

    base_dir_path = _worktree_base_dir(cfg, repo_dir)
    worktree_path = (base_dir_path / session_id).resolve()

    branch_prefix = cfg.get("branchPrefix", "session/")
    branch_name = f"{branch_prefix}{session_id}"
    return worktree_path, branch_name


def _get_worktree_base() -> Path:
    """Compute worktree base directory."""
    cfg = _config().get_worktree_config()
    repo_dir = _get_repo_dir()
    return _worktree_base_dir(cfg, repo_dir)
