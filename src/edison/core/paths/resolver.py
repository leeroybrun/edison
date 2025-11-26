"""Centralized path resolution for Edison framework.

This module provides canonical path resolution patterns to eliminate
duplication across 50+ scripts. All path resolution MUST use these helpers
to ensure consistent behavior across tests, CLIs, and library code.

Key features:
- Project root detection with environment variable priority
- Evidence directory resolution with round detection
- Session ID detection from multiple sources
- Fail-fast validation to prevent .edison directory confusion

See `.project/qa/EDISON_NO_LEGACY_POLICY.md` for configuration and migration rules.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List
from edison.core.utils.subprocess import run_with_timeout
from edison.core.file_io.utils import read_json_safe
from .management import get_management_paths
from .project import DEFAULT_PROJECT_CONFIG_PRIMARY, get_project_config_dir


class EdisonPathError(ValueError):
    """Raised when path resolution fails.

    This includes:
    - Cannot resolve project root
    - Project root resolves to .edison directory (invalid)
    - Evidence directory not found
    - Invalid session ID format
    """
    pass


class PathResolver:
    """Centralized path resolution for Edison framework.

    This class provides static methods for all path resolution patterns
    used across the Edison framework. All methods are fail-fast and raise
    EdisonPathError on failures rather than returning None or invalid paths.

    Examples:
        >>> root = PathResolver.resolve_project_root()
        >>> evidence = PathResolver.find_evidence_round("task-100", round=2)
        >>> session_id = PathResolver.detect_session_id()
    """

    @staticmethod
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

        Examples:
            >>> root = PathResolver.resolve_project_root()
            >>> assert root.name != ".edison"
            >>> assert (root / ".project").exists() or (root / ".edison").exists()
        """
        # Simple in-process memoization: avoid repeated filesystem/git calls.
        # The cache is deliberately process-wide so that scripts and libraries
        # sharing this module perform root resolution at most once.
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

        # Local project root shortcut: honor a .project directory in CWD, but avoid
        # treating the Edison framework checkout (.edison/core) as a project root.
        cwd = Path.cwd().resolve()

        # If we're somewhere inside .edison/core (the framework itself), prefer the
        # outer project directory that owns .edison rather than the inner framework
        # checkout which carries its own .project folder for internal metadata.
        edison_core_root = next(
            (p for p in [cwd, *cwd.parents] if p.name == "core" and p.parent.name == ".edison"),
            None,
        )
        if edison_core_root is not None:
            owner_project_root = edison_core_root.parent.parent
            if owner_project_root.exists():
                if _PROJECT_ROOT_CACHE != owner_project_root:
                    _PROJECT_ROOT_CACHE = owner_project_root
                return owner_project_root

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

    @staticmethod
    def detect_session_id(
        explicit: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """Canonical session ID detection with validation.

        Detection priority:
        1. Explicit session ID parameter (if provided)
        2. project_SESSION environment variable (canonical)
        3. Auto-detect from owner / project_OWNER

        Auto-detection from owner looks for sessions in
        ``.project/sessions/active/`` whose ``session.json`` contains
        a matching ``owner`` field.

        Args:
            explicit: Explicit session ID if provided by caller
            owner: Owner name for auto-detection

        Returns:
            str: Normalized session ID, or None if cannot detect

        Raises:
            EdisonPathError: If session ID format is invalid

        Examples:
            >>> sid = PathResolver.detect_session_id(explicit="sess-123")
            >>> assert sid == "sess-123"

            >>> os.environ["project_SESSION"] = "my-session"
            >>> sid = PathResolver.detect_session_id()
            >>> assert sid == "my-session"
        """
        # Priority 1: Explicit parameter
        if explicit:
            return PathResolver._validate_session_id(explicit)

        # Priority 2: project_SESSION environment variable (canonical)
        project_session = os.environ.get("project_SESSION")
        if project_session:
            return PathResolver._validate_session_id(project_session)

        # Priority 3: Auto-detect from owner / project_OWNER
        if owner is None:
            owner = os.environ.get("project_OWNER")

        if owner:
            try:
                root = PathResolver.resolve_project_root()
                mgmt_paths = get_management_paths(root)
                sessions_active = mgmt_paths.get_session_state_dir("active")

                if not sessions_active.exists():
                    return None

                # Look for session directories with matching owner
                for session_dir in sessions_active.iterdir():
                    if not session_dir.is_dir():
                        continue

                    session_json = session_dir / "session.json"
                    if not session_json.exists():
                        continue

                    try:
                        data = read_json_safe(session_json, default={})
                        if isinstance(data, dict) and data.get("owner") == owner:
                            return PathResolver._validate_session_id(session_dir.name)
                    except Exception:
                        continue
            except EdisonPathError:
                pass

        return None

    @staticmethod
    def _validate_session_id(session_id: str) -> str:
        """Validate session ID format.

        Session IDs must:
        - Be non-empty
        - Contain only alphanumeric, dash, and underscore characters
        - Not contain path traversal sequences
        - Be 64 characters or less

        Args:
            session_id: Session ID to validate

        Returns:
            str: Validated session ID

        Raises:
            EdisonPathError: If session ID is invalid
        """
        if not session_id:
            raise EdisonPathError("Session ID cannot be empty")

        if len(session_id) > 64:
            raise EdisonPathError(
                f"Session ID too long: {len(session_id)} characters (max 64)"
            )

        # Check for path traversal
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise EdisonPathError(
                f"Session ID contains path traversal or separators: {session_id}"
            )

        # Check for valid characters (alphanumeric, dash, underscore)
        if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
            raise EdisonPathError(
                f"Session ID contains invalid characters: {session_id}. "
                "Only alphanumeric, dash, and underscore allowed."
            )

        return session_id

    @staticmethod
    def find_evidence_round(
        task_id: str,
        round: Optional[int] = None,
    ) -> Path:
        """Evidence directory resolution with round detection.

        Resolution logic:
        - If round is specified: .project/qa/validation-evidence/{task_id}/round-{round}/
        - If round is None: Find latest round-N directory

        Args:
            task_id: Task ID (e.g., "task-100" or "100")
            round: Specific round number, or None for latest

        Returns:
            Path: Evidence directory path

        Raises:
            EdisonPathError: If evidence directory not found

        Examples:
            >>> latest = PathResolver.find_evidence_round("task-100")
            >>> round_2 = PathResolver.find_evidence_round("task-100", round=2)
        """
        root = PathResolver.resolve_project_root()
        mgmt_paths = get_management_paths(root)
        evidence_base = mgmt_paths.get_qa_root() / "validation-evidence" / task_id

        if not evidence_base.exists():
            raise EdisonPathError(
                f"Evidence directory does not exist: {evidence_base}"
            )

        # If specific round requested, return it
        if round is not None:
            round_dir = evidence_base / f"round-{round}"
            if not round_dir.exists():
                raise EdisonPathError(
                    f"Evidence round-{round} not found for task {task_id}: {round_dir}"
                )
            return round_dir

        # Find latest round
        rounds = sorted(
            [p for p in evidence_base.glob("round-*") if p.is_dir()],
            key=lambda p: int(p.name.split("-")[1])
            if p.name.split("-")[1].isdigit()
            else 0,
        )

        if not rounds:
            raise EdisonPathError(
                f"No evidence rounds found for task {task_id} in {evidence_base}"
            )

        return rounds[-1]

    @staticmethod
    def list_evidence_rounds(task_id: str) -> List[Path]:
        """List all evidence round directories for a task.

        Args:
            task_id: Task ID

        Returns:
            List[Path]: Sorted list of round directories (oldest to newest)

        Examples:
            >>> rounds = PathResolver.list_evidence_rounds("task-100")
            >>> assert all(r.name.startswith("round-") for r in rounds)
        """
        root = PathResolver.resolve_project_root()
        mgmt_paths = get_management_paths(root)
        evidence_base = mgmt_paths.get_qa_root() / "validation-evidence" / task_id

        if not evidence_base.exists():
            return []

        rounds = sorted(
            [p for p in evidence_base.glob("round-*") if p.is_dir()],
            key=lambda p: int(p.name.split("-")[1])
            if p.name.split("-")[1].isdigit()
            else 0,
        )

        return rounds

    @staticmethod
    def get_project_path(*parts: str) -> Path:
        """Get path relative to project root: .project/{parts}.

        Args:
            *parts: Path components to append to .project/

        Returns:
            Path: Absolute path under .project/

        Examples:
            >>> tasks_dir = PathResolver.get_project_path("tasks", "todo")
            >>> sessions_dir = PathResolver.get_project_path("sessions", "active")
        """
        root = PathResolver.resolve_project_root()
        mgmt_paths = get_management_paths(root)
        return (mgmt_paths.get_management_root() / Path(*parts)).resolve()

    @staticmethod
    def get_edison_core_path(*parts: str) -> Path:
        """Get path relative to Edison core: .edison/core/{parts}.

        Args:
            *parts: Path components to append to .edison/core/

        Returns:
            Path: Absolute path under .edison/core/

        Examples:
            >>> lib_dir = PathResolver.get_edison_core_path("lib")
            >>> schema = PathResolver.get_edison_core_path("schemas", "task.schema.json")
        """
        root = PathResolver.resolve_project_root()
        return (root / ".edison" / "core" / Path(*parts)).resolve()


# Convenience functions for common operations


def resolve_project_root() -> Path:
    """Convenience wrapper for PathResolver.resolve_project_root()."""
    return PathResolver.resolve_project_root()


def detect_session_id(
    explicit: Optional[str] = None,
    owner: Optional[str] = None,
) -> Optional[str]:
    """Convenience wrapper for PathResolver.detect_session_id()."""
    return PathResolver.detect_session_id(explicit=explicit, owner=owner)


def find_evidence_round(task_id: str, round: Optional[int] = None) -> Path:
    """Convenience wrapper for PathResolver.find_evidence_round()."""
    return PathResolver.find_evidence_round(task_id, round=round)


def is_git_repository(path: Path) -> bool:
    """Return True if ``path`` is inside a git repository.

    Walks up parent directories looking for a ``.git`` entry (file or
    directory). This is a lightweight structural check and does not run
    git commands, making it safe to call in non-git sandboxes.

    Args:
        path: Filesystem path to probe.

    Returns:
        bool: True if a ``.git`` entry is found, otherwise False.
    """
    p = Path(path).resolve()
    # If a file is passed, start from its parent directory
    if p.is_file():
        p = p.parent
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return True
    return False


def get_git_root(path: Path) -> Optional[Path]:
    """Return the git repository root for ``path``, or None if not in a repo.

    This mirrors :func:`is_git_repository` by walking parents looking for a
    ``.git`` entry, but returns the first directory that contains it.

    Args:
        path: Filesystem path to probe.

    Returns:
        Optional[Path]: Git repository root directory, or None when no
        repository is detected.
    """
    p = Path(path).resolve()
    if p.is_file():
        p = p.parent
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


_PROJECT_ROOT_CACHE: Optional[Path] = None


__all__ = [
    "EdisonPathError",
    "PathResolver",
    "resolve_project_root",
    "detect_session_id",
    "find_evidence_round",
    "is_git_repository",
    "get_git_root",
    "_PROJECT_ROOT_CACHE",
]
