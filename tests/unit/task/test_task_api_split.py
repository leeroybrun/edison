from __future__ import annotations

import json
from pathlib import Path

from edison.core.task import io, locking, record_metadata, paths
from edison.core.utils.io import write_json_atomic


def test_paths_session_state_dir_returns_path() -> None:
    session_dir = paths.session_state_dir("todo")
    assert isinstance(session_dir, Path)


def test_io_atomic_write_json_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    payload = {"hello": "world", "n": 1}

    write_json_atomic(target, payload, indent=2)

    result = json.loads(target.read_text(encoding="utf-8"))
    assert result == payload


def test_locking_safe_move_file_preserves_content(tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    dest = tmp_path / "nested" / "dest.txt"
    src.write_text("keep me", encoding="utf-8")

    moved = locking.safe_move_file(src, dest)

    assert moved == dest
    assert dest.read_text(encoding="utf-8") == "keep me"


def test_metadata_read_metadata_extracts_owner_and_status(tmp_path: Path) -> None:
    path = tmp_path / "task.md"
    path.write_text(
        f"{paths.OWNER_PREFIX_TASK}alice\n{paths.STATUS_PREFIX}wip\n",
        encoding="utf-8",
    )

    meta = record_metadata.read_metadata(path, "task")

    assert meta.owner == "alice"
    assert meta.status == "wip"
