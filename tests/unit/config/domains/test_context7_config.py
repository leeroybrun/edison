from __future__ import annotations

from pathlib import Path

import pytest

from edison.data import get_data_path, read_yaml


@pytest.fixture()
def context7_config_path() -> Path:
    return get_data_path("config", "context7.yaml")


def test_context7_config_file_exists(context7_config_path: Path) -> None:
    assert context7_config_path.exists(), "context7.yaml must exist in bundled config"


def test_context7_yaml_parses(context7_config_path: Path) -> None:
    cfg = read_yaml("config", "context7.yaml")
    assert isinstance(cfg, dict), "YAML should parse into a mapping"
    assert cfg, "YAML content should not be empty"


def test_context7_metadata_present() -> None:
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    assert section.get("version"), "Config must declare schema version"
    assert section.get("trainingCutoff"), "Config must declare trainingCutoff"


def test_context7_core_is_tech_agnostic() -> None:
    """Core context7.yaml must not embed technology-specific package metadata.

    Technology-specific triggers/aliases/packages are provided by packs and/or project overlays.
    """
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    assert section.get("triggers", {}) == {}
    assert section.get("aliases", {}) == {}
    assert section.get("packages", {}) == {}
