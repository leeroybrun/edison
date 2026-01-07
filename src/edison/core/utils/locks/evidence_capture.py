"""Coarse locks for evidence capture concurrency control."""

from __future__ import annotations

import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from edison.core.utils.io.locking import LockTimeoutError, acquire_file_lock
from edison.core.utils.paths.management import get_management_paths
from edison.core.utils.locks.file_metadata import write_lock_metadata


def _slug(value: str) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "default"


def evidence_capture_lock_path(*, project_root: Path, command_group: str) -> Path:
    qa_root = get_management_paths(project_root).get_qa_root()
    locks_dir = qa_root / "locks"
    return locks_dir / f"evidence-capture-{_slug(command_group)}.lock"


@contextmanager
def acquire_evidence_capture_lock(
    *,
    project_root: Path,
    command_group: str,
    session_id: str | None = None,
    timeout_seconds: float | None = None,
) -> Iterator[dict[str, Any]]:
    """Acquire a coarse evidence capture lock for the given command group.

    Returns a dict with:
    - lockKey: stable key string
    - lockPath: lock file path
    - waitedMs: time spent waiting to acquire the lock
    """
    lock_path = evidence_capture_lock_path(project_root=project_root, command_group=command_group)
    start = time.monotonic()

    try:
        with acquire_file_lock(
            lock_path,
            timeout=timeout_seconds,
            nfs_safe=False,
            fail_open=False,
            repo_root=project_root,
        ) as fh:
            waited_ms = int((time.monotonic() - start) * 1000)
            try:
                if fh is not None:
                    write_lock_metadata(
                        fh,
                        pid=os.getpid(),
                        meta={
                            "sessionId": session_id or "",
                            "commandGroup": str(command_group),
                        },
                    )
            except Exception:
                # Best-effort metadata; lock safety comes from OS lock, not the file contents.
                pass

            yield {
                "lockKey": f"evidence-capture:{_slug(command_group)}",
                "lockPath": str(lock_path),
                "waitedMs": waited_ms,
            }
    except LockTimeoutError as exc:
        holder = ""
        try:
            holder = lock_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            holder = ""
        msg = (
            f"Timed out waiting for evidence capture lock (group={command_group}) at {lock_path}."
            + (f" Last holder: {holder}" if holder else "")
        )
        raise RuntimeError(msg) from exc


__all__ = ["acquire_evidence_capture_lock", "evidence_capture_lock_path"]
