from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_task_lock_times_out_when_already_held(isolated_project_env: Path) -> None:
    from edison.core.qa.locks.task import acquire_qa_task_lock

    task_id = "T-LOCK-1"
    acquired = threading.Event()
    released = threading.Event()
    errors: list[BaseException] = []

    def holder() -> None:
        try:
            with acquire_qa_task_lock(
                project_root=isolated_project_env,
                task_id=task_id,
                purpose="validate",
                session_id="sid-1",
                timeout_seconds=1.0,
            ):
                acquired.set()
                released.wait(timeout=2.0)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    t = threading.Thread(target=holder, daemon=True)
    t.start()
    assert acquired.wait(timeout=1.0)

    # Attempt to acquire while held: should timeout quickly.
    started = time.monotonic()
    with pytest.raises(RuntimeError):
        with acquire_qa_task_lock(
            project_root=isolated_project_env,
            task_id=task_id,
            purpose="validate",
            session_id="sid-2",
            timeout_seconds=0.1,
        ):
            pass
    assert (time.monotonic() - started) < 1.0

    released.set()
    t.join(timeout=2.0)
    assert not errors
