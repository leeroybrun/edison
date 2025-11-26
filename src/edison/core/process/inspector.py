"""
Process tree inspection for session ID inference.

Walks up the process tree to find the topmost Edison or LLM process,
then generates a PID-based session identifier.

IMPORTANT
---------
This module reuses the psutil/is_process_alive pattern from
``scripts/tasks/cleanup-stale-locks`` for consistency. Keep the
behaviour aligned with that script whenever changes are made here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:  # Optional dependency
    import psutil  # type: ignore

    HAS_PSUTIL = True
except ImportError:  # pragma: no cover - handled at runtime
    HAS_PSUTIL = False

DEFAULT_LLM_NAMES = ["claude", "codex", "gemini", "cursor", "aider", "happy"]
DEFAULT_EDISON_NAMES = ["edison", "python"]  # python when running Edison scripts
DEFAULT_EDISON_MARKERS = ["edison", ".edison", "scripts/tasks", "scripts/session", "scripts/qa"]

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "process.yaml"


def _load_config() -> Dict[str, object]:
    """Load process inspection config from YAML if present.

    Returns an empty dict if the file is missing or unreadable. YAML parsing
    failures are swallowed to keep process inference best-effort.
    """

    if not _CONFIG_PATH.exists():
        return {}

    try:
        from edison.core.file_io.utils import read_yaml_safe

        data = read_yaml_safe(_CONFIG_PATH, default={})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_llm_process_names() -> List[str]:
    """Load LLM process names from configuration with safe defaults."""

    cfg = _load_config()
    names = cfg.get("llm_processes") if isinstance(cfg.get("llm_processes"), list) else DEFAULT_LLM_NAMES
    return [str(n).lower() for n in names if str(n).strip()]


def _load_edison_process_names() -> List[str]:
    """Load Edison process names from configuration with safe defaults."""

    cfg = _load_config()
    names = cfg.get("edison_processes") if isinstance(cfg.get("edison_processes"), list) else DEFAULT_EDISON_NAMES
    return [str(n).lower() for n in names if str(n).strip()]


def _load_edison_script_markers() -> List[str]:
    """Load command-line markers that indicate Edison scripts."""

    cfg = _load_config()
    markers = cfg.get("edison_script_markers") if isinstance(cfg.get("edison_script_markers"), list) else DEFAULT_EDISON_MARKERS
    return [str(m).lower() for m in markers if str(m).strip()]


def _is_edison_script(cmdline: List[str]) -> bool:
    """Check if a command line indicates an Edison script invocation."""

    cmdline_str = " ".join(cmdline).lower()
    return any(marker in cmdline_str for marker in _load_edison_script_markers())


def is_process_alive(pid: int) -> bool:
    """Check if a process is alive by PID.

    Uses the same pattern as ``scripts/tasks/cleanup-stale-locks``:
    - Prefer ``psutil.pid_exists`` when psutil is installed
    - Fallback to ``os.kill(pid, 0)`` where supported
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


def find_topmost_process() -> Tuple[str, int]:
    """Walk up process tree to find the topmost Edison or LLM process.

    Priority order:
    1) Edison process (wins over LLM if encountered)
    2) LLM process (used if no Edison found)
    3) Current process (fallback when psutil unavailable or nothing matches)
    """

    if not HAS_PSUTIL:
        return ("python", os.getpid())

    try:
        llm_names = _load_llm_process_names()
        edison_names = _load_edison_process_names()

        current = psutil.Process(os.getpid())
        highest_match: Optional[Tuple[str, int]] = None

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

            # Edison check (highest priority)
            if name in edison_names:
                if name == "python":
                    if _is_edison_script(cmdline):
                        highest_match = ("edison", current.pid)
                else:
                    highest_match = ("edison", current.pid)

            # LLM check only if no Edison seen yet
            elif name in llm_names and (not highest_match or highest_match[0] != "edison"):
                highest_match = (name, current.pid)

            try:
                parent = current.parent()
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                break

            current = parent

        if highest_match:
            return highest_match

        # Fallback: default to current PID with generic python label
        return ("python", os.getpid())

    except Exception:
        # Final fallback if anything unexpected occurs
        return ("python", os.getpid())


def infer_session_id() -> str:
    """Infer a session ID from the process tree.

    Returns:
        Session ID in the form ``{process-name}-pid-{pid}``
    """

    process_name, pid = find_topmost_process()
    return f"{process_name}-pid-{pid}"
