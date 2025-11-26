from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json
import threading

import pytest

import edison.core.file_io.utils as io_utils
from edison.core.file_io.locking import LockTimeoutError, acquire_file_lock
from edison.core.file_io.utils import read_json_safe, utc_timestamp, write_json_safe


def test_write_json_safe_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "data.json"
    payload: Dict[str, Any] = {"a": 1, "b": {"c": [1, 2, 3]}}
    write_json_safe(out, payload)

    assert out.exists()
    data = json.loads(out.read_text())
    assert data == payload

    # Overwrite
    payload2 = {"a": 2}
    write_json_safe(out, payload2)
    assert json.loads(out.read_text()) == payload2


def test_read_json_safe_missing_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        read_json_safe(missing)


def test_concurrent_atomic_writes_produce_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "race.json"

    def writer(value: int) -> None:
        for _ in range(50):
            write_json_safe(out, {"v": value})

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(2,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # File must contain a complete JSON object with either value 1 or 2
    data = json.loads(out.read_text())
    assert data.get("v") in (1, 2)


def test_utc_timestamp_is_iso_utc() -> None:
    ts = utc_timestamp()
    # datetime.fromisoformat accepts "+00:00"; ensure no exception
    from datetime import datetime
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_atomic_write_honors_lock_context(tmp_path: Path) -> None:
    locked = tmp_path / "nested" / "locked.json"

    # Hold the lock to force a timeout in the nested writer
    with acquire_file_lock(locked, timeout=0.5):
        with pytest.raises(LockTimeoutError):
            io_utils._atomic_write(  # type: ignore[attr-defined]
                locked,
                lambda f: f.write("late"),
                lock_cm=acquire_file_lock(locked, timeout=0.1, fail_open=False),
            )

    # Once the lock is released, the write should succeed with the provided lock
    io_utils._atomic_write(  # type: ignore[attr-defined]
        locked,
        lambda f: f.write("ok"),
        lock_cm=acquire_file_lock(locked, timeout=0.5, fail_open=False),
    )

    assert locked.read_text() == "ok"
