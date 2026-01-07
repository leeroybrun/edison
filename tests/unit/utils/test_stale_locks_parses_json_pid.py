from __future__ import annotations

import json
from pathlib import Path

from edison.core.utils.io.stale_locks import inspect_lock


def test_inspect_lock_parses_json_pid(tmp_path: Path) -> None:
    lock_path = tmp_path / "lock.lock"
    lock_path.write_text(json.dumps({"pid": 12345, "sessionId": "sess-1"}), encoding="utf-8")

    pid, pid_alive = inspect_lock(lock_path)
    assert pid == 12345
    # We don't assert pid_alive since the process won't exist in tests.

