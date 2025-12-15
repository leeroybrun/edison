"""TDD tests for `edison config show --format yaml` output validity.

These tests ensure YAML output is syntactically valid, including when selecting a single key.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("key", ["delegation", "validation", "context7"])
def test_config_show_key_yaml_is_parseable(tmp_path: Path, key: str) -> None:
    """`edison config show <key> --format yaml` must emit valid YAML."""
    # Minimal project config root (optional, but keeps path resolution consistent).
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["edison", "config", "show", key, "--format", "yaml", "--repo-root", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    parsed = yaml.safe_load(result.stdout)
    assert isinstance(parsed, dict)
    assert key in parsed


def test_config_show_full_yaml_is_parseable(tmp_path: Path) -> None:
    """`edison config show --format yaml` must emit valid YAML for the full config."""
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["edison", "config", "show", "--format", "yaml", "--repo-root", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    parsed = yaml.safe_load(result.stdout)
    assert isinstance(parsed, dict)
    assert "project" in parsed

