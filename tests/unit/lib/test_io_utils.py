"""Tests for edison.core.io_utils module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edison.core.utils.io import (
    read_json,
    write_json_atomic,
    ensure_parent_dir,
)
from edison.core.utils.time import utc_timestamp


def test_utc_timestamp_returns_iso_format():
    """UTC timestamp returns ISO 8601 format string."""
    ts = utc_timestamp()
    # Should be a valid ISO 8601 timestamp
    assert "T" in ts
    assert ts.endswith("Z") or "+" in ts or "-" in ts[-6:]


def test_read_json_returns_dict_for_valid_json(tmp_path: Path):
    """read_json returns dict for valid JSON file."""
    data = {"key": "value", "number": 42}
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data))

    result = read_json(json_file)
    assert result == data


def test_read_json_raises_for_missing_file(tmp_path: Path):
    """read_json raises FileNotFoundError for missing file."""
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        read_json(missing)


def test_write_json_atomic_creates_file(tmp_path: Path):
    """write_json_atomic creates JSON file."""
    data = {"test": "data"}
    output = tmp_path / "output.json"

    write_json_atomic(output, data)

    assert output.exists()
    assert json.loads(output.read_text()) == data


def test_ensure_parent_dir_creates_parents(tmp_path: Path):
    """ensure_parent_dir creates parent directories."""
    nested = tmp_path / "a" / "b" / "c" / "file.txt"

    ensure_parent_dir(nested)

    assert nested.parent.exists()
    assert nested.parent.is_dir()
