from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from edison.core.file_io.locking import LockTimeoutError, acquire_file_lock


def test_acquire_file_lock_can_fail_open(tmp_path: Path) -> None:
    target = tmp_path / "data.json"

    holder_ready = threading.Event()
    holder_done = threading.Event()

    def _holder() -> None:
        with acquire_file_lock(target, timeout=0.5):
            holder_ready.set()
            time.sleep(0.3)
            holder_done.set()

    thread = threading.Thread(target=_holder)
    thread.start()

    assert holder_ready.wait(timeout=1)
    start = time.monotonic()

    with acquire_file_lock(target, timeout=0.05, fail_open=True):
        elapsed = time.monotonic() - start
        # Fail-open should return quickly instead of blocking for holder duration
        assert elapsed < 0.2
        target.write_text("ok", encoding="utf-8")

    thread.join()
    assert holder_done.is_set()
    assert target.read_text(encoding="utf-8") == "ok"


def test_acquire_file_lock_times_out_without_fail_open(tmp_path: Path) -> None:
    target = tmp_path / "guard.json"

    with acquire_file_lock(target, timeout=0.5):
        with pytest.raises(LockTimeoutError):
            with acquire_file_lock(target, timeout=0.05, fail_open=False):
                target.write_text("should not happen", encoding="utf-8")
