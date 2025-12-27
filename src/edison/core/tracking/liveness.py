from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any

from edison.core.utils.config import load_validated_section
from edison.core.utils.time import parse_iso8601, utc_now


def pid_is_running(*, process_id: Any, hostname: Any) -> bool | None:
    """Best-effort liveness check for a PID on the current host.

    Returns:
        - True/False when liveness can be determined locally
        - None when liveness cannot be determined (e.g., remote host or invalid PID)
    """
    try:
        pid = int(process_id)
    except Exception:
        return None

    host = str(hostname or "").strip()
    if host and host != socket.gethostname():
        return None

    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return None
    return True


def active_stale_seconds(*, repo_root: Path | None) -> int:
    cfg = load_validated_section(
        ["orchestration", "tracking"],
        required_fields=["activeStaleSeconds"],
        repo_root=repo_root,
    )
    return int(cfg["activeStaleSeconds"])


def is_stale(*, repo_root: Path | None, last_active: Any) -> bool | None:
    try:
        ts = str(last_active or "").strip()
        if not ts:
            return None
        last_dt = parse_iso8601(ts, repo_root=repo_root)
        now_dt = utc_now(repo_root=repo_root)
        age_seconds = (now_dt - last_dt).total_seconds()
        return age_seconds > float(active_stale_seconds(repo_root=repo_root))
    except Exception:
        return None


__all__ = ["pid_is_running", "is_stale", "active_stale_seconds"]
