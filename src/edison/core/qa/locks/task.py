"""Per-task locks for QA round operations and validation execution.

Goal: allow concurrent validation of different tasks, but prevent concurrent
operations on the same task/bundle root (which causes nondeterministic reads of
round artifacts and validator reports).
"""

from __future__ import annotations

import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from edison.core.utils.io.locking import LockTimeoutError, acquire_file_lock
from edison.core.utils.locks.named import named_lock_path
from edison.core.utils.locks.file_metadata import write_lock_metadata


def _slug(value: str) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "default"


def qa_task_lock_path(*, project_root: Path, task_id: str, purpose: str) -> Path:
    return named_lock_path(
        repo_root=project_root,
        namespace=f"qa_{_slug(purpose)}",
        key=_slug(task_id),
        scope="repo",
    )


@contextmanager
def acquire_qa_task_lock(
    *,
    project_root: Path,
    task_id: str,
    purpose: str,
    session_id: str | None = None,
    timeout_seconds: float | None = None,
) -> Iterator[dict[str, Any]]:
    """Acquire an exclusive lock for task_id + purpose (fail-closed)."""
    lock_path = qa_task_lock_path(project_root=project_root, task_id=task_id, purpose=purpose)
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
                            "taskId": str(task_id),
                            "purpose": str(purpose),
                        },
                    )
            except Exception:
                pass

            yield {
                "lockKey": f"qa:{_slug(purpose)}:{_slug(task_id)}",
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
            f"Timed out waiting for QA lock (purpose={purpose}, task={task_id}) at {lock_path}."
            + (f" Last holder: {holder}" if holder else "")
        )
        raise RuntimeError(msg) from exc


__all__ = ["acquire_qa_task_lock", "qa_task_lock_path"]
