"""T-063: Wilson project overlay entity examples must exist and be structured.

Validates presence and structure of Wilson-specific entity example documents in
the project overlay. All expectations are configured via YAML to avoid
hardcoded paths or section names.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from edison.core.paths.project import get_project_config_dir
from edison.core.paths.resolver import PathResolver


CONFIG_FILE = "wilson_entity_examples.yaml"


def _load_examples_config(repo_root: Path) -> dict:
    """Load YAML-backed contract for Wilson entity example documents."""

    project_config_dir = get_project_config_dir(repo_root)
    config_path = project_config_dir / "config" / CONFIG_FILE

    assert config_path.exists(), f"Entity examples config missing at {config_path}"

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    examples = cfg.get("entity_examples") or {}

    required_keys = ("base_dir", "required_sections", "entities")
    missing = [key for key in required_keys if not examples.get(key)]
    if missing:
        pytest.fail(
            f"wilson_entity_examples.yaml missing required keys: {', '.join(missing)}"
        )

    return examples


def _assert_overlay_path(base_dir: Path, project_config_dir: Path) -> None:
    """Ensure the configured base_dir stays inside the project overlay."""

    overlay_root = project_config_dir.resolve()
    base_dir_resolved = base_dir.resolve()
    if not str(base_dir_resolved).startswith(str(overlay_root)):
        pytest.fail(
            f"Configured base_dir {base_dir_resolved} must live inside {overlay_root}"
        )


def test_entity_examples_exist_and_cover_required_sections() -> None:
    """Example markdown files must exist and include configured sections."""

    repo_root = PathResolver.resolve_project_root()
    cfg = _load_examples_config(repo_root)

    base_dir = repo_root / cfg["base_dir"]
    project_config_dir = get_project_config_dir(repo_root)
    _assert_overlay_path(base_dir, project_config_dir)

    assert base_dir.exists(), f"Entity examples directory missing at {base_dir}"

    required_sections = [str(section).lower() for section in cfg["required_sections"]]

    for entity in cfg.get("entities", []):
        filename = entity.get("filename")
        key = entity.get("key") or filename

        assert filename, "Each entity entry must include a filename"

        example_path = base_dir / filename
        assert example_path.exists(), f"Example for {key} missing at {example_path}"

        content = example_path.read_text(encoding="utf-8").lower()
        for section in required_sections:
            assert section in content, f"{key} example missing section: {section}"
