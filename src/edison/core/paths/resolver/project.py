"""Project root resolution logic."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from edison.core.paths.management import get_management_paths
from edison.core.paths.resolver.base import EdisonPathError, get_git_root

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
            raise EdisonPathError(f"{env_var_used} points at missing path: {env_path}")
        if env_path.name == ".edison":
            raise EdisonPathError(
                f"{env_var_used} points to .edison directory: {env_path}. "
                "This is invalid - must point to project root."
            )
        if _PROJECT_ROOT_CACHE != env_path:
            _PROJECT_ROOT_CACHE = env_path
        return env_path

    # Local project root shortcut: honor a .project directory in CWD
    cwd = Path.cwd().resolve()

    if (cwd / ".project").exists():
        if cwd.name == ".edison":
            raise EdisonPathError(
                "Refusing to use .edison as project root even though .project exists"
            )
        if _PROJECT_ROOT_CACHE != cwd:
            _PROJECT_ROOT_CACHE = cwd
        return cwd

    # With no environment override, reuse cached value only when it still
    # looks like a valid project root (contains .project or .edison).
    if _PROJECT_ROOT_CACHE is not None:
        if (_PROJECT_ROOT_CACHE / ".project").exists() or (_PROJECT_ROOT_CACHE / ".edison").exists():
            return _PROJECT_ROOT_CACHE
        # Stale cache from a temp env-root without markers; discard and
        # fall through to git-based detection.
        _PROJECT_ROOT_CACHE = None

    # Priority 2: Use git to discover the repository root
    cwd = Path.cwd().resolve()
    try:
        from edison.core.utils.subprocess import run_with_timeout  # local import to avoid circular dependency

        result = run_with_timeout(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=True,
            timeout_type="git_operations",
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
    if path.name == ".edison":
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
    root = resolve_project_root()
    mgmt_paths = get_management_paths(root)
    return (mgmt_paths.get_management_root() / Path(*parts)).resolve()
