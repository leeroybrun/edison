"""Process tree inspection for session ID inference.

Walks up the process tree to find the topmost Edison or LLM process,
then generates a PID-based session identifier.

IMPORTANT
---------
psutil is a required dependency as of task 001-session-id-inference.
This ensures stable process tree inference across all platforms and
IDE wrappers (Claude, Codex, Cursor, etc.).
"""
from __future__ import annotations

import os

from functools import lru_cache
import psutil  # Required dependency - stable process tree inference

HAS_PSUTIL = True  # Always True since psutil is now required


def _project_root_key() -> str:
    """Best-effort cache key for process detection configuration."""
    try:
        from edison.core.utils.paths import PathResolver

        return str(PathResolver.resolve_project_root())
    except Exception:
        return ""


@lru_cache(maxsize=32)
def _cached_llm_process_names(project_root: str) -> tuple[str, ...]:
    try:
        from pathlib import Path

        from edison.core.config.domains.process import ProcessConfig

        root = Path(project_root).expanduser().resolve() if project_root else None
        if root is None:
            raise ValueError("missing project root")
        return tuple(ProcessConfig(repo_root=root).get_llm_processes())
    except Exception:
        return ("claude", "codex", "gemini", "cursor", "aider", "happy", "opencode")


def _load_llm_process_names() -> list[str]:
    """Load LLM process names from configuration with safe defaults."""
    return list(_cached_llm_process_names(_project_root_key()))


@lru_cache(maxsize=32)
def _cached_llm_script_markers(project_root: str) -> tuple[str, ...]:
    try:
        from pathlib import Path

        from edison.core.config.domains.process import ProcessConfig

        root = Path(project_root).expanduser().resolve() if project_root else None
        if root is None:
            raise ValueError("missing project root")
        return tuple(ProcessConfig(repo_root=root).get_llm_script_markers())
    except Exception:
        return ("happy", "claude", "codex", "cursor", "gemini", "aider", "opencode")


def _load_llm_script_markers() -> list[str]:
    """Load command-line markers that indicate an LLM wrapper CLI."""
    return list(_cached_llm_script_markers(_project_root_key()))

@lru_cache(maxsize=32)
def _cached_llm_marker_map(project_root: str) -> dict[str, str]:
    try:
        from pathlib import Path

        from edison.core.config.domains.process import ProcessConfig

        root = Path(project_root).expanduser().resolve() if project_root else None
        if root is None:
            raise ValueError("missing project root")
        return dict(ProcessConfig(repo_root=root).get_llm_marker_map())
    except Exception:
        return {
            "happy": "happy",
            "claude": "claude",
            "codex": "codex",
            "cursor": "cursor",
            "gemini": "gemini",
            "aider": "aider",
            "opencode": "opencode",
        }


def _load_llm_marker_map() -> dict[str, str]:
    """Load marker -> canonical wrapper name mapping."""
    return dict(_cached_llm_marker_map(_project_root_key()))

@lru_cache(maxsize=32)
def _cached_llm_cmdline_excludes(project_root: str) -> dict[str, list[str]]:
    try:
        from pathlib import Path

        from edison.core.config.domains.process import ProcessConfig

        root = Path(project_root).expanduser().resolve() if project_root else None
        if root is None:
            raise ValueError("missing project root")
        return dict(ProcessConfig(repo_root=root).get_llm_cmdline_excludes())
    except Exception:
        return {}


def _load_llm_cmdline_excludes() -> dict[str, list[str]]:
    """Load wrapper-specific cmdline substrings to exclude from LLM detection."""
    return dict(_cached_llm_cmdline_excludes(_project_root_key()))

@lru_cache(maxsize=32)
def _cached_edison_process_names(project_root: str) -> tuple[str, ...]:
    try:
        from pathlib import Path

        from edison.core.config.domains.process import ProcessConfig

        root = Path(project_root).expanduser().resolve() if project_root else None
        if root is None:
            raise ValueError("missing project root")
        return tuple(ProcessConfig(repo_root=root).get_edison_processes())
    except Exception:
        return ("edison", "python")


def _load_edison_process_names() -> list[str]:
    """Load Edison process names from configuration with safe defaults."""
    return list(_cached_edison_process_names(_project_root_key()))


@lru_cache(maxsize=32)
def _cached_edison_script_markers(project_root: str) -> tuple[str, ...]:
    try:
        from pathlib import Path

        from edison.core.config.domains.process import ProcessConfig

        root = Path(project_root).expanduser().resolve() if project_root else None
        if root is None:
            raise ValueError("missing project root")
        return tuple(ProcessConfig(repo_root=root).get_edison_script_markers())
    except Exception:
        try:
            from edison.core.utils.paths import PathResolver, get_project_config_dir

            return ("edison", get_project_config_dir(PathResolver.resolve_project_root(), create=False).name.lower())
        except Exception:
            return ("edison", ".edison")


def _load_edison_script_markers() -> list[str]:
    """Load command-line markers that indicate Edison scripts."""
    return list(_cached_edison_script_markers(_project_root_key()))


def reset_process_detection_caches() -> None:
    """Clear cached process detection configuration (primarily for tests)."""
    _cached_llm_process_names.cache_clear()
    _cached_llm_script_markers.cache_clear()
    _cached_llm_marker_map.cache_clear()
    _cached_llm_cmdline_excludes.cache_clear()
    _cached_edison_process_names.cache_clear()
    _cached_edison_script_markers.cache_clear()


def _is_edison_script(cmdline: list[str]) -> bool:
    """Check if a command line indicates an Edison script invocation."""
    cmdline_str = " ".join(cmdline).lower()
    return any(marker in cmdline_str for marker in _load_edison_script_markers())


def _match_llm_wrapper(name: str, cmdline: list[str]) -> str | None:
    """Return canonical wrapper name if this process appears to be an LLM wrapper."""
    llm_names = [n.strip().lower() for n in _load_llm_process_names() if str(n).strip()]
    cmdline_str = " ".join(cmdline).lower()

    candidate: str | None = None
    if name in llm_names:
        candidate = name
    else:
        markers = [m.strip().lower() for m in _load_llm_script_markers() if str(m).strip()]
        marker_map = {
            str(k).strip().lower(): str(v).strip().lower()
            for k, v in _load_llm_marker_map().items()
        }
        for marker in markers:
            if marker and marker in cmdline_str:
                candidate = marker_map.get(marker, marker)
                break

    if not candidate:
        return None

    excludes = _load_llm_cmdline_excludes().get(candidate, [])
    if excludes and any(str(x).strip().lower() in cmdline_str for x in excludes if str(x).strip()):
        return None

    return candidate


def is_process_alive(pid: int) -> bool:
    """Check if a process is alive by PID.

    Uses the same pattern as ``edison tasks cleanup-stale-locks``:
    - Prefer ``psutil.pid_exists`` when psutil is installed
    - Fallback to ``os.kill(pid, 0)`` where supported

    Args:
        pid: Process ID to check

    Returns:
        bool: True if the process is alive
    """
    if HAS_PSUTIL:
        try:
            return psutil.pid_exists(pid)
        except Exception:
            pass

    # Portable-ish fallback: kill(pid, 0) raises OSError when pid doesn't exist
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # Permission denied implies the process exists but is protected
        return True
    except OSError:
        return False


def find_topmost_process() -> tuple[str, int]:
    """Walk up process tree to find the topmost Edison or LLM process.

    Edison and LLM processes have equal weight - we simply find whichever
    is highest in the process tree. This handles cases like:
    - edison1 -> llm -> edison2: returns edison1
    - llm1 -> edison1 -> llm2 -> edison2: returns llm1
    - edison orchestrator launch -> claude: returns edison

    Fallback: current process PID when nothing matches.

    Returns:
        Tuple[str, int]: (process_name, pid) of the topmost matching process
    """
    try:
        return _find_topmost_process_from(psutil.Process(os.getpid()))

    except Exception:
        # Final fallback if anything unexpected occurs
        return ("python", os.getpid())

def _find_topmost_process_from(start: psutil.Process) -> tuple[str, int]:
    """Internal helper to find the topmost-of-either match from an arbitrary start process.

    This is used for deterministic unit tests without relying on the real OS process tree.
    """
    edison_names = _load_edison_process_names()

    current = start
    highest_match: tuple[str, int] | None = None

    while current:
        try:
            name_raw = (current.name() or "").lower()
            name = "python" if name_raw.startswith("python") else name_raw
        except psutil.AccessDenied:
            name = ""
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            break

        try:
            cmdline = current.cmdline()
        except psutil.AccessDenied:
            cmdline = []
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            break

        # Check for LLM wrapper (by name OR cmdline markers). Always update highest_match.
        llm_name = _match_llm_wrapper(name, cmdline)
        if llm_name:
            highest_match = (llm_name, current.pid)

        # Check for Edison process - always update highest_match when found
        elif name in edison_names:
            if name == "python":
                # For python processes, verify it's actually running Edison
                if _is_edison_script(cmdline):
                    highest_match = ("edison", current.pid)
            else:
                highest_match = ("edison", current.pid)

        try:
            parent = current.parent()
            if parent is None:
                break
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
            break

        current = parent

    if highest_match:
        return highest_match

    # Fallback: default to current PID with generic python label
    return ("python", os.getpid())


def infer_session_id() -> str:
    """Infer a session ID from the process tree.

    Returns:
        str: Session ID in the form ``{process-name}-pid-{pid}``
    """
    process_name, pid = find_topmost_process()
    return f"{process_name}-pid-{pid}"


def get_current_owner() -> str:
    """Get the current owner identifier based on process tree.

    The owner is used to identify which process/user owns a session.
    It's derived from the topmost process in the tree.

    Returns:
        str: Owner identifier in the form ``{process-name}-pid-{pid}``

    Note:
        This is the same as infer_session_id() but named for semantic clarity
        when looking up sessions by owner.
    """
    process_name, pid = find_topmost_process()
    return f"{process_name}-pid-{pid}"


__all__ = [
    "HAS_PSUTIL",
    "is_process_alive",
    "find_topmost_process",
    "_find_topmost_process_from",
    "infer_session_id",
    "get_current_owner",
]
