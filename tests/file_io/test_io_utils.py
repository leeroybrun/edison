from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json
import threading

import pytest

import edison.core.file_io.utils as io_utils
from edison.core.file_io.locking import LockTimeoutError, acquire_file_lock
from edison.core.file_io.utils import read_json_safe, write_json_safe
from edison.core.utils.time import utc_timestamp


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
    # datetime.fromisoformat needs 'Z' replaced with '+00:00' for Python < 3.11
    from datetime import datetime
    ts_compat = ts.replace('Z', '+00:00') if ts.endswith('Z') else ts
    parsed = datetime.fromisoformat(ts_compat)
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


def test_read_json_safe_invalid_json_raises(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{unquoted: invalid}", encoding="utf-8")
    
    with pytest.raises(json.JSONDecodeError):
        read_json_safe(invalid)




# ============================================================================
# YAML I/O Tests
# ============================================================================

def test_read_yaml_safe_with_valid_file(tmp_path: Path) -> None:
    """Test read_yaml_safe with valid YAML file."""
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

    data = io_utils.read_yaml_safe(yaml_file)
    assert data is not None
    assert data["name"] == "test"
    assert data["version"] == 1.0
    assert data["features"] == ["feature1", "feature2"]
    assert data["nested"]["key"] == "value"


def test_read_yaml_safe_with_missing_file(tmp_path: Path) -> None:
    """Test read_yaml_safe returns default when file is missing."""
    missing = tmp_path / "missing.yaml"

    # Default None
    result = io_utils.read_yaml_safe(missing)
    assert result is None

    # Custom default
    result = io_utils.read_yaml_safe(missing, default={})
    assert result == {}

    result = io_utils.read_yaml_safe(missing, default={"fallback": True})
    assert result == {"fallback": True}


def test_read_yaml_safe_with_invalid_yaml(tmp_path: Path) -> None:
    """Test read_yaml_safe returns default when YAML is invalid."""
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("{ invalid: yaml: structure", encoding="utf-8")

    # Should return default instead of raising
    result = io_utils.read_yaml_safe(invalid, default={})
    assert result == {}


def test_read_yaml_safe_with_empty_file(tmp_path: Path) -> None:
    """Test read_yaml_safe with empty YAML file."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")

    # Empty YAML file should return default
    result = io_utils.read_yaml_safe(empty, default={})
    assert result == {}


def test_write_yaml_safe_creates_file(tmp_path: Path) -> None:
    """Test write_yaml_safe creates file atomically."""
    yaml_file = tmp_path / "nested" / "output.yaml"
    data = {
        "name": "test",
        "version": 1.0,
        "features": ["feature1", "feature2"],
        "nested": {"key": "value"}
    }

    io_utils.write_yaml_safe(yaml_file, data)

    assert yaml_file.exists()
    # Read back and verify
    result = io_utils.read_yaml_safe(yaml_file)
    assert result == data


def test_write_yaml_safe_overwrites_existing(tmp_path: Path) -> None:
    """Test write_yaml_safe overwrites existing file."""
    yaml_file = tmp_path / "overwrite.yaml"

    # Write first version
    data1 = {"version": 1}
    io_utils.write_yaml_safe(yaml_file, data1)
    assert io_utils.read_yaml_safe(yaml_file) == data1

    # Overwrite with second version
    data2 = {"version": 2, "new_key": "value"}
    io_utils.write_yaml_safe(yaml_file, data2)
    assert io_utils.read_yaml_safe(yaml_file) == data2


def test_write_yaml_safe_with_sorted_keys(tmp_path: Path) -> None:
    """Test write_yaml_safe produces deterministic sorted output."""
    yaml_file = tmp_path / "sorted.yaml"
    data = {"z": 1, "a": 2, "m": 3}

    io_utils.write_yaml_safe(yaml_file, data)

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

    io_utils.write_yaml_safe(yaml_file, original_data)
    read_data = io_utils.read_yaml_safe(yaml_file)

    assert read_data == original_data


def test_yaml_concurrent_atomic_writes(tmp_path: Path) -> None:
    """Test concurrent YAML writes produce valid YAML files."""
    yaml_file = tmp_path / "concurrent.yaml"

    def writer(value: int) -> None:
        for _ in range(30):
            io_utils.write_yaml_safe(yaml_file, {"counter": value})

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # File must contain valid YAML with either value 1 or 2
    result = io_utils.read_yaml_safe(yaml_file)
    assert result is not None
    assert result.get("counter") in (1, 2)
