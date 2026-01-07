"""Shared helpers for lock metadata files.

Edison uses OS-level file locks for safety. Some workflows also write a small
metadata payload into the locked file so operators can understand who holds it.

This module centralizes that metadata format to avoid drift across subsystems.
"""

from __future__ import annotations

import json
import os
from typing import Any, TextIO

from edison.core.utils.time import utc_timestamp


def write_lock_metadata(
    fh: TextIO,
    *,
    pid: int | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Best-effort: overwrite lock file contents with a small metadata payload.

    Format:
    - First line: `pid=<pid>` (easy to parse without JSON)
    - Second line: JSON object (optional, for richer debugging)
    """
    try:
        payload: dict[str, Any] = dict(meta or {})
        if pid is None:
            pid = os.getpid()
        payload.setdefault("pid", int(pid))
        payload.setdefault("acquiredAt", utc_timestamp())

        fh.seek(0)
        fh.truncate(0)
        fh.write(f"pid={payload['pid']}\n")
        fh.write(json.dumps(payload, sort_keys=True))
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    except Exception:
        # Metadata is debug-only. Lock correctness is provided by OS locking.
        return


__all__ = ["write_lock_metadata"]

