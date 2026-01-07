from __future__ import annotations

import json
from pathlib import Path

from edison.core.utils.locks.file_metadata import write_lock_metadata


def test_write_lock_metadata_writes_pid_line_and_json(tmp_path: Path) -> None:
    path = tmp_path / "demo.lock"
    with path.open("a+", encoding="utf-8") as fh:
        write_lock_metadata(fh, pid=123, meta={"purpose": "test"})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "pid=123"

    payload = json.loads(lines[1])
    assert payload["pid"] == 123
    assert payload["purpose"] == "test"
    assert "acquiredAt" in payload

