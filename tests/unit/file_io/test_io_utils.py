from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json
import threading

import pytest

import edison.core.utils.io as io_utils
from edison.core.utils.io import (
    read_json,
    write_json_atomic,
    read_yaml,
    write_yaml,
    atomic_write,
    ensure_parent_dir,
)
from edison.core.utils.io.locking import LockTimeoutError, acquire_file_lock
from edison.core.utils.time import utc_timestamp
from tests.helpers.timeouts import LOCK_TIMEOUT


def test_write_json_atomic_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "data.json"
    payload: Dict[str, Any] = {"a": 1, "b": {"c": [1, 2, 3]}}
    write_json_atomic(out, payload)

    assert out.exists()
    data = json.loads(out.read_text())
    assert data == payload

    # Overwrite
    payload2 = {"a": 2}
    write_json_atomic(out, payload2)
    assert json.loads(out.read_text()) == payload2


def test_read_json_missing_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        read_json(missing)


def test_concurrent_atomic_writes_produce_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "race.json"

    def writer(value: int) -> None:
        for _ in range(50):
            write_json_atomic(out, {"v": value})

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(2,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # File must contain a complete JSON object with either value 1 or 2
    data = json.loads(out.read_text())
    assert data.get("v") in (1, 2)


def test_utc_timestamp_is_iso_utc() -> None:
    ts = utc_timestamp()
    # datetime.fromisoformat needs 'Z' replaced with '+00:00' for Python < 3.11
    from datetime import datetime
    ts_compat = ts.replace('Z', '+00:00') if ts.endswith('Z') else ts
    parsed = datetime.fromisoformat(ts_compat)
    assert parsed.tzinfo is not None


def test_atomic_write_honors_lock_context(tmp_path: Path) -> None:
    locked = tmp_path / "nested" / "locked.json"

    # Hold the lock to force a timeout in the nested writer
    with acquire_file_lock(locked, timeout=LOCK_TIMEOUT / 4):
        with pytest.raises(LockTimeoutError):
            atomic_write(
                locked,
                lambda f: f.write("late"),
                lock_cm=acquire_file_lock(locked, timeout=LOCK_TIMEOUT / 20, fail_open=False),
            )

    # Once the lock is released, the write should succeed with the provided lock
    atomic_write(
        locked,
        lambda f: f.write("ok"),
        lock_cm=acquire_file_lock(locked, timeout=LOCK_TIMEOUT / 4, fail_open=False),
    )

    assert locked.read_text() == "ok"


def test_read_json_invalid_json_raises(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{unquoted: invalid}", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        read_json(invalid)


def test_ensure_parent_dir_creates_parents(tmp_path: Path) -> None:
    """ensure_parent_dir creates parent directories."""
    nested = tmp_path / "a" / "b" / "c" / "file.txt"

    ensure_parent_dir(nested)

    assert nested.parent.exists()
    assert nested.parent.is_dir()


def test_write_text_accepts_encoding_kwarg(tmp_path: Path) -> None:
    """write_text should allow callers to specify the text encoding."""
    out = tmp_path / "out.txt"
    io_utils.write_text(out, "hello", encoding="utf-8")
    assert out.read_text(encoding="utf-8") == "hello"

# ============================================================================
# YAML I/O Tests
# ============================================================================
def test_read_yaml_with_valid_file(tmp_path: Path) -> None:
    """Test read_yaml with valid YAML file."""
    yaml_file = tmp_path / "config.yaml"
    yaml_content = """
name: test
version: 1.0
features:
  - feature1
  - feature2
nested:
  key: value
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    data = read_yaml(yaml_file)
    assert data is not None
    assert data["name"] == "test"
    assert data["version"] == 1.0
    assert data["features"] == ["feature1", "feature2"]
    assert data["nested"]["key"] == "value"


def test_read_yaml_with_missing_file(tmp_path: Path) -> None:
    """Test read_yaml returns default when file is missing."""
    missing = tmp_path / "missing.yaml"

    # Default None
    result = read_yaml(missing)
    assert result is None

    # Custom default
    result = read_yaml(missing, default={})
    assert result == {}

    result = read_yaml(missing, default={"fallback": True})
    assert result == {"fallback": True}


def test_read_yaml_with_invalid_yaml(tmp_path: Path) -> None:
    """Test read_yaml returns default when YAML is invalid."""
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("{ invalid: yaml: structure", encoding="utf-8")

    # Should return default instead of raising
    result = read_yaml(invalid, default={})
    assert result == {}


def test_read_yaml_with_empty_file(tmp_path: Path) -> None:
    """Test read_yaml with empty YAML file."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")

    # Empty YAML file should return default
    result = read_yaml(empty, default={})
    assert result == {}


def test_write_yaml_creates_file(tmp_path: Path) -> None:
    """Test write_yaml creates file atomically."""
    yaml_file = tmp_path / "nested" / "output.yaml"
    data = {
        "name": "test",
        "version": 1.0,
        "features": ["feature1", "feature2"],
        "nested": {"key": "value"}
    }

    write_yaml(yaml_file, data)

    assert yaml_file.exists()
    # Read back and verify
    result = read_yaml(yaml_file)
    assert result == data


def test_write_yaml_overwrites_existing(tmp_path: Path) -> None:
    """Test write_yaml overwrites existing file."""
    yaml_file = tmp_path / "overwrite.yaml"

    # Write first version
    data1 = {"version": 1}
    write_yaml(yaml_file, data1)
    assert read_yaml(yaml_file) == data1

    # Overwrite with second version
    data2 = {"version": 2, "new_key": "value"}
    write_yaml(yaml_file, data2)
    assert read_yaml(yaml_file) == data2


def test_write_yaml_with_sorted_keys(tmp_path: Path) -> None:
    """Test write_yaml produces deterministic sorted output."""
    yaml_file = tmp_path / "sorted.yaml"
    data = {"z": 1, "a": 2, "m": 3}

    write_yaml(yaml_file, data)

    content = yaml_file.read_text()
    lines = content.strip().split("\n")
    # Keys should appear in sorted order
    assert lines[0].startswith("a:")
    assert lines[1].startswith("m:")
    assert lines[2].startswith("z:")


def test_yaml_roundtrip_consistency(tmp_path: Path) -> None:
    """Test YAML write-read roundtrip maintains data integrity."""
    yaml_file = tmp_path / "roundtrip.yaml"

    original_data = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "boolean": True,
        "null_value": None,
        "list": [1, 2, 3],
        "nested": {
            "deep": {
                "value": "test"
            }
        }
    }

    write_yaml(yaml_file, original_data)
    read_data = read_yaml(yaml_file)

    assert read_data == original_data


def test_yaml_concurrent_atomic_writes(tmp_path: Path) -> None:
    """Test concurrent YAML writes produce valid YAML files."""
    yaml_file = tmp_path / "concurrent.yaml"

    def writer(value: int) -> None:
        for _ in range(30):
            write_yaml(yaml_file, {"counter": value})

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # File must contain valid YAML with either value 1 or 2
    result = read_yaml(yaml_file)
    assert result is not None
    assert result.get("counter") in (1, 2)
