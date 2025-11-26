"""T-041: Guard rail for Wilson architecture guideline completeness.

Ensures the Wilson project architecture guide exists and is not truncated.
Configuration (path, required sections, conclusion marker) lives in the
project overlay (`.edison/config`) to keep core resources project-agnostic and
YAML-driven.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from edison.core.utils.paths.project import get_project_config_dir
from edison.core.utils.paths.resolver import PathResolver


CONFIG_FILE = "wilson_architecture.yaml"


def _load_architecture_config(repo_root: Path) -> dict:
    """Load YAML-backed contract for the Wilson architecture guide."""

    project_config_dir = get_project_config_dir(repo_root)
    config_path = project_config_dir / "config" / CONFIG_FILE

    if not config_path.exists():
        pytest.skip("wilson_architecture.yaml not present in project config overlay")

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    architecture = cfg.get("architecture") or {}

    required_keys = ("path", "required_headings", "conclusion_marker", "min_lines")
    missing = [key for key in required_keys if not architecture.get(key)]
    if missing:
        pytest.fail(
            f"wilson_architecture.yaml missing required keys: {', '.join(missing)}"
        )

    return architecture


def test_wilson_architecture_exists_and_is_complete() -> None:
    """Architecture guide must exist and end with the configured conclusion."""

    repo_root = PathResolver.resolve_project_root()
    cfg = _load_architecture_config(repo_root)
    doc_path = repo_root / cfg["path"]

    assert doc_path.exists(), f"Architecture guide missing at {doc_path}"

    content = doc_path.read_text(encoding="utf-8").rstrip()
    lines = [line.rstrip() for line in content.splitlines()]

    assert len(lines) >= int(cfg["min_lines"]), "Architecture guide appears truncated"

    lower_content = content.lower()
    for heading in cfg.get("required_headings", []):
        assert heading.lower() in lower_content, f"Missing section: {heading}"

    conclusion_marker = str(cfg["conclusion_marker"]).strip()
    assert content.endswith(conclusion_marker), "Architecture guide does not end with the configured conclusion"
