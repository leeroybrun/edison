"""Tests for tests/helpers/io_utils.py module.

Validates centralized I/O utilities for test files, ensuring
they create parent directories and handle file operations correctly.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from helpers.io_utils import write_yaml, write_json, write_config, write_text, write_guideline


def test_write_yaml_creates_parent_dirs(tmp_path: Path) -> None:
    """write_yaml creates parent directories if they don't exist."""
    nested_path = tmp_path / "a" / "b" / "c" / "test.yml"
    data = {"key": "value", "nested": {"foo": "bar"}}

    write_yaml(nested_path, data)

    assert nested_path.exists()
    loaded = yaml.safe_load(nested_path.read_text(encoding="utf-8"))
    assert loaded == data


def test_write_yaml_with_sort_keys(tmp_path: Path) -> None:
    """write_yaml respects sort_keys parameter."""
    path = tmp_path / "sorted.yml"
    data = {"zebra": 1, "alpha": 2, "beta": 3}

    write_yaml(path, data, sort_keys=True)

    content = path.read_text(encoding="utf-8")
    lines = [line for line in content.split('\n') if line.strip()]
    # With sort_keys=True, 'alpha' should appear before 'zebra'
    assert lines.index("alpha: 2") < lines.index("zebra: 1")


def test_write_json_creates_parent_dirs(tmp_path: Path) -> None:
    """write_json creates parent directories if they don't exist."""
    nested_path = tmp_path / "x" / "y" / "z" / "test.json"
    data = {"test": "data", "number": 42}

    write_json(nested_path, data)

    assert nested_path.exists()
    import json
    loaded = json.loads(nested_path.read_text(encoding="utf-8"))
    assert loaded == data


def test_write_json_with_custom_indent(tmp_path: Path) -> None:
    """write_json respects indent parameter."""
    path = tmp_path / "indented.json"
    data = {"key": "value"}

    write_json(path, data, indent=4)

    content = path.read_text(encoding="utf-8")
    # 4-space indent
    assert "    " in content


def test_write_config_creates_edison_config_structure(tmp_path: Path) -> None:
    """write_config creates .edison/config/ directory structure."""
    content = "test: value\n"

    result = write_config(tmp_path, content)

    assert result.exists()
    assert result == tmp_path / ".edison" / "config" / "config.yml"
    assert result.read_text(encoding="utf-8") == content


def test_write_config_with_custom_filename(tmp_path: Path) -> None:
    """write_config respects custom filename parameter."""
    content = "custom: content\n"

    result = write_config(tmp_path, content, filename="custom.yaml")

    assert result.exists()
    assert result == tmp_path / ".edison" / "config" / "custom.yaml"
    assert result.read_text(encoding="utf-8") == content


def test_write_text_creates_parent_dirs(tmp_path: Path) -> None:
    """write_text creates parent directories if they don't exist."""
    nested_path = tmp_path / "deep" / "nested" / "path" / "file.txt"
    content = "Hello, World!\n"

    write_text(nested_path, content)

    assert nested_path.exists()
    assert nested_path.read_text(encoding="utf-8") == content


def test_write_guideline_creates_parent_dirs(tmp_path: Path) -> None:
    """write_guideline creates parent directories if they don't exist."""
    nested_path = tmp_path / "guidelines" / "subdir" / "GUIDE.md"
    content = "# Guideline\n\n<!-- ANCHOR: test -->\nContent\n<!-- END ANCHOR: test -->\n"

    write_guideline(nested_path, content)

    assert nested_path.exists()
    assert nested_path.read_text(encoding="utf-8") == content


def test_write_guideline_handles_markdown(tmp_path: Path) -> None:
    """write_guideline correctly writes Markdown content."""
    path = tmp_path / "TEST.md"
    content = "\n".join([
        "# Test Guidelines",
        "",
        "<!-- ANCHOR: validation -->",
        "Validation content here.",
        "<!-- END ANCHOR: validation -->",
    ])

    write_guideline(path, content)

    assert path.exists()
    written = path.read_text(encoding="utf-8")
    assert "# Test Guidelines" in written
    assert "<!-- ANCHOR: validation -->" in written
    assert "Validation content here." in written
