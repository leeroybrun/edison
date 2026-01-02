"""Centralized path resolution for Edison framework.

This module provides canonical path resolution patterns to eliminate
duplication across 50+ scripts. All path resolution MUST use these helpers
to ensure consistent behavior across tests, CLIs, and library code.

Path resolution follows these principles:
- Framework defaults come from edison.data package (bundled)
- Project config comes from .edison/config/ (project overrides)
- Generated files go to .edison/_generated/
- NO legacy .edison/core/ paths
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from .errors import EdisonPathError

# Cache for project root to avoid repeated filesystem/git calls
_PROJECT_ROOT_CACHE: Optional[Path] = None


def resolve_project_root() -> Path:
    """Resolve project root with fail-fast validation.

    Resolution priority:
    1. AGENTS_PROJECT_ROOT environment variable
    2. Git repository root via ``git rev-parse --show-toplevel``

    The resolution MUST NOT resolve to the .edison directory itself.
    This prevents scripts from treating .edison as a project when run
    from within the framework directory.

    Returns:
        Path: Absolute path to project root

    Raises:
        EdisonPathError: If cannot resolve or resolves to .edison directory
    """
    global _PROJECT_ROOT_CACHE

    # Best-effort marker names for lightweight root validation without config loads.
    # These can be overridden via env vars (same paths as ConfigManager supports).
    project_config_dir_name = (
        os.environ.get("EDISON_paths__project_config_dir")
        or os.environ.get("EDISON_paths__config_dir")
        or ".edison"
    )
    project_management_dir_name = (
        os.environ.get("EDISON_project_management_dir")
        or os.environ.get("EDISON_paths__management_dir")
        or ".project"
    )

    # Priority 1: environment overrides. Always honour them, even when a
    # cache is already populated from previous calls inside the same
    # process (common in test suites).
    env_path: Optional[Path] = None
    env_var_used: Optional[str] = None
    for env_var in ("AGENTS_PROJECT_ROOT",):
        env_root = os.environ.get(env_var)
        if env_root:
            env_path = Path(env_root).expanduser().resolve()
            env_var_used = env_var
            break

    # Environment override has absolute priority to support isolated test
    # projects; honour it before any CWD heuristics or cached values.
    if env_path is not None:
        if not env_path.exists():
            raise EdisonPathError(
                f"{env_var_used} points at missing path: {env_path}"
            )
        if env_path.name in {".edison", project_config_dir_name}:
            raise EdisonPathError(
                f"{env_var_used} points to .edison directory: {env_path}. "
                "This is invalid - must point to project root."
            )
        if _PROJECT_ROOT_CACHE != env_path:
            _PROJECT_ROOT_CACHE = env_path
        return env_path

    # Local project root shortcut: honor a .project directory in CWD
    cwd = Path.cwd().resolve()

    if (cwd / project_management_dir_name).exists():
        if cwd.name in {".edison", project_config_dir_name}:
            raise EdisonPathError(
                "Refusing to use .edison as project root even though .project exists"
            )
        if _PROJECT_ROOT_CACHE != cwd:
            _PROJECT_ROOT_CACHE = cwd
        return cwd

    # With no environment override, reuse cached value only when the caller is
    # still operating *inside* that project root. This keeps performance wins
    # for repeated calls while preserving correctness for test suites (or other
    # long-running processes) that chdir into other repositories.
    if _PROJECT_ROOT_CACHE is not None:
        if cwd == _PROJECT_ROOT_CACHE or _PROJECT_ROOT_CACHE in cwd.parents:
            if (_PROJECT_ROOT_CACHE / project_management_dir_name).exists() or (
                _PROJECT_ROOT_CACHE / project_config_dir_name
            ).exists():
                return _PROJECT_ROOT_CACHE
            # Stale cache from a temp env-root without markers; discard and
            # fall through to git-based detection.
            _PROJECT_ROOT_CACHE = None

    # Priority 2: Use git to discover the repository root.
    #
    # IMPORTANT: This must not depend on Edison config (timeouts, packs, etc.),
    # because config loading itself can require a resolved project root.
    cwd = Path.cwd().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        raise EdisonPathError(
            "git executable not found on PATH; "
            "set AGENTS_PROJECT_ROOT to your project root."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise EdisonPathError(
            "Unable to resolve project root via git. "
            "Set AGENTS_PROJECT_ROOT or run inside a git repository."
        ) from exc

    root_str = (result.stdout or "").strip()
    if not root_str:
        raise EdisonPathError(
            "git rev-parse --show-toplevel returned empty output; "
            "ensure this process is running inside a git repository."
        )

    path = Path(root_str).expanduser().resolve()
    if not path.exists():
        raise EdisonPathError(
            f"git rev-parse --show-toplevel resolved to non-existent path: {path}"
        )

    # If git reports the .edison directory as the toplevel, we are most
    # likely running inside the Edison framework checkout that lives
    # inside a larger project repository. In that case, treat the owning
    # project repository (the one that contains .edison/) as the canonical
    # project root instead of .edison itself.
    if path.name in {".edison", project_config_dir_name}:
        # Lazy import to avoid circular dependency
        from edison.core.utils.git import get_git_root

        parent_git_root = get_git_root(path.parent)
        if parent_git_root is not None and parent_git_root != path:
            path = parent_git_root
        else:
            raise EdisonPathError(
                f"Resolved project root is the .edison directory ({path}); "
                "this is invalid. Run commands from the project repo root "
                "or set AGENTS_PROJECT_ROOT explicitly."
            )

    _PROJECT_ROOT_CACHE = path
    return path


def get_project_path(*parts: str) -> Path:
    """Get path relative to project root: .project/{parts}.

    Args:
        *parts: Path components to append to .project/

    Returns:
        Path: Absolute path under .project/
    """
    # Lazy import to avoid circular dependency
    from .management import get_management_paths

    root = resolve_project_root()
    mgmt_paths = get_management_paths(root)
    return (mgmt_paths.get_management_root() / Path(*parts)).resolve()


class PathResolver:
    """Centralized path resolution for Edison framework.

    This class provides static methods for all path resolution patterns
    used across the Edison framework. All methods are fail-fast and raise
    EdisonPathError on failures rather than returning None or invalid paths.
    """

    @staticmethod
    def resolve_project_root() -> Path:
        """Resolve project root with fail-fast validation."""
        return resolve_project_root()

    @staticmethod
    def detect_session_id(
        explicit: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """Canonical session ID detection with validation."""
        # Lazy import - session ID detection is in session module
        from edison.core.session.core.id import detect_session_id

        return detect_session_id(explicit=explicit, owner=owner)

    @staticmethod
    def _validate_session_id(session_id: str) -> str:
        """Validate session ID format."""
        # Lazy import - session ID validation is in session module
        from edison.core.session.core.id import validate_session_id

        return validate_session_id(session_id)

    @staticmethod
    def find_evidence_round(
        task_id: str,
        round: Optional[int] = None,
    ) -> Path:
        """Evidence directory resolution with round detection."""
        from .evidence import find_evidence_round

        return find_evidence_round(task_id, round=round)

    @staticmethod
    def list_evidence_rounds(task_id: str) -> List[Path]:
        """List all evidence round directories for a task."""
        from .evidence import list_evidence_rounds

        return list_evidence_rounds(task_id)

    @staticmethod
    def get_project_path(*parts: str) -> Path:
        """Get path relative to project root: .project/{parts}."""
        return get_project_path(*parts)


__all__ = [
    "EdisonPathError",
    "PathResolver",
    "resolve_project_root",
    "get_project_path",
    "_PROJECT_ROOT_CACHE",
]
