from __future__ import annotations

import importlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from helpers.io_utils import write_yaml


@pytest.fixture()
def json_module(isolated_project_env: Path):
    # Write config with specific json_io settings for testing
    cfg = {
        "json_io": {
            "indent": 2,
            "sort_keys": True,
            "ensure_ascii": False,
        },
        "timeouts": {
            "git_operations_seconds": 60.0,
            "db_operations_seconds": 30.0,
            "json_io_lock_seconds": 5.0,
        },
        "subprocess_timeouts": {
            "default": 5.0,
            "git_operations": 5.0,
            "file_operations": 5.0,
        },
        "file_locking": {
            "timeout_seconds": 5.0,
            "poll_interval_seconds": 0.1,
        },
    }
    write_yaml(isolated_project_env / ".edison" / "core" / "config" / "defaults.yaml", cfg)
    import edison.core.utils.io.json as json_io  # type: ignore

    importlib.reload(json_io)
    return json_io


def test_write_and_read_json_respects_config(json_module, tmp_path: Path):
    path = tmp_path / "data.json"
    json_module.write_json_atomic(path, {"b": 2, "a": 1})

    text = path.read_text(encoding="utf-8")
    # indent=2 and sort_keys=True come from YAML config
    assert '"a": 1' in text.splitlines()[1]

    data = json_module.read_json(path)
    assert data == {"a": 1, "b": 2}


def test_update_json_is_atomic(json_module, tmp_path: Path):
    path = tmp_path / "counter.json"
    json_module.write_json_atomic(path, {"count": 1})

    def _update(data):
        data["count"] = 2
        raise RuntimeError("fail mid‑update")

    with pytest.raises(RuntimeError):
        json_module.update_json(path, _update)

    # File must remain unchanged and no temp files should linger
    assert json_module.read_json(path)["count"] == 1
    leftovers = [p for p in path.parent.glob("counter.json*") if p != path]
    assert leftovers == []


def test_update_json_is_thread_safe(json_module, tmp_path: Path):
    path = tmp_path / "threaded.json"
    json_module.write_json_atomic(path, {"hits": 0})

    def bump():
        def _inc(data):
            data["hits"] += 1
            return data

        json_module.update_json(path, _inc)

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda _: bump(), range(10)))

    assert json_module.read_json(path)["hits"] == 10
