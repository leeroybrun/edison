"""Shared configuration helpers for worktree modules."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from edison.core.utils.paths import PathResolver
from edison.core.config.domains.project import ProjectConfig
from .._config import get_config

if TYPE_CHECKING:
    from edison.core.config.domains import SessionConfig


def _config() -> "SessionConfig":
    """Return the cached SessionConfig instance.
    
    This is a convenience wrapper for worktree modules.
    """
    return get_config()


def _get_repo_dir() -> Path:
    """Get the repository root directory."""
    return PathResolver.resolve_project_root()


def _get_project_name() -> str:
    """Resolve the active project name via ConfigManager."""
    return ProjectConfig().name


def _worktree_base_dir(cfg: Dict[str, Any], repo_dir: Path) -> Path:
    """Compute the worktree base directory from configuration.

    Args:
        cfg: Worktree configuration dictionary
        repo_dir: Repository root directory

    Returns:
        Resolved path to worktree base directory
    """
    base_dir_value = cfg.get("baseDirectory") or "../{PROJECT_NAME}-worktrees"
    substituted = ProjectConfig(repo_root=repo_dir).substitute_project_tokens(str(base_dir_value))
    base_dir_path = Path(substituted)
    if base_dir_path.is_absolute():
        return base_dir_path
    anchor = repo_dir if (base_dir_path.parts and base_dir_path.parts[0] == "..") else repo_dir.parent
    return (anchor / base_dir_path).resolve()


def _resolve_worktree_target(session_id: str, cfg: Dict[str, Any]) -> tuple[Path, str]:
    """Compute worktree path and branch name from config and session id.
    
    Args:
        session_id: Session identifier
        cfg: Worktree configuration dictionary
        
    Returns:
        Tuple of (worktree_path, branch_name)
    """
    repo_dir = _get_repo_dir()

    base_dir_path = _worktree_base_dir(cfg, repo_dir)
    worktree_path = (base_dir_path / session_id).resolve()

    branch_prefix = cfg.get("branchPrefix", "session/")
    branch_name = f"{branch_prefix}{session_id}"
    return worktree_path, branch_name


def _resolve_archive_directory(cfg: Dict[str, Any], repo_dir: Path) -> Path:
    """Resolve the worktree archive directory from configuration.

    This is the canonical implementation of archive directory resolution.
    It consolidates the logic previously duplicated in cleanup.py and manager.py.

    Args:
        cfg: Worktree configuration dictionary
        repo_dir: Repository root directory

    Returns:
        Resolved path to archive directory
    """
    raw = cfg.get("archiveDirectory", ".worktrees/archive")
    raw_path = Path(raw)
    if raw_path.is_absolute():
        return raw_path
    # Paths starting with ".worktrees" are anchored to repo_dir
    # All other relative paths are anchored to repo_dir.parent
    anchor = repo_dir if str(raw).startswith(".worktrees") else repo_dir.parent
    return (anchor / raw).resolve()


def _get_worktree_base() -> Path:
    """Compute worktree base directory using centralized config.

    This is the canonical function for getting the worktree base directory.
    All other code should import and use this function.

    Returns:
        Resolved path to worktree base directory
    """
    cfg = get_config().get_worktree_config()
    repo_dir = _get_repo_dir()
    return _worktree_base_dir(cfg, repo_dir)
