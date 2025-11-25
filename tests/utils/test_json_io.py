from __future__ import annotations

import importlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml


def _write_json_config(repo_root: Path) -> None:
    cfg = {
        "json_io": {
            "indent": 2,
            "sort_keys": True,
            "ensure_ascii": False,
        },
        "subprocess_timeouts": {
            "default": 5.0,
            "git_operations": 5.0,
            "file_operations": 5.0,
        },
    }
    cfg_dir = repo_root / ".edison" / "core" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.joinpath("defaults.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")


@pytest.fixture()
def json_module(isolated_project_env: Path):
    _write_json_config(isolated_project_env)
    import edison.core.utils.json_io as json_io  # type: ignore

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
