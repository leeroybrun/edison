from __future__ import annotations

from pathlib import Path

import pytest

from edison.data import get_data_path, read_yaml


@pytest.fixture()
def post_training_config_path() -> Path:
    return get_data_path("config", "post_training_packages.yaml")


def test_post_training_packages_file_exists(post_training_config_path: Path) -> None:
    assert post_training_config_path.exists(), "post_training_packages.yaml must exist in bundled config"


def test_post_training_packages_yaml_parses(post_training_config_path: Path) -> None:
    cfg = read_yaml("config", "post_training_packages.yaml")
    assert isinstance(cfg, dict), "YAML should parse into a mapping"
    assert cfg, "YAML content should not be empty"


def test_post_training_packages_metadata_present() -> None:
    cfg = read_yaml("config", "post_training_packages.yaml")
    assert cfg.get("version"), "Config must declare schema version"
    assert cfg.get("trainingCutoff"), "Config must declare trainingCutoff"


def test_post_training_packages_include_all_packages() -> None:
    cfg = read_yaml("config", "post_training_packages.yaml")
    packages = cfg.get("packages", {})
    expected = {"next", "react", "tailwindcss", "zod", "motion", "typescript", "prisma", "better-auth"}
    missing = expected.difference(packages.keys())
    assert not missing, f"Missing expected packages: {sorted(missing)}"


def test_post_training_packages_have_required_fields() -> None:
    cfg = read_yaml("config", "post_training_packages.yaml")
    packages = cfg.get("packages", {})

    required_fields = {"version", "context7Id", "criticalChanges", "topics"}

    for name, pkg in packages.items():
        present = required_fields.intersection(pkg.keys())
        assert present == required_fields, f"Package '{name}' missing fields: {sorted(required_fields - present)}"
        assert isinstance(pkg["criticalChanges"], list) and pkg["criticalChanges"], (
            f"Package '{name}' must list criticalChanges"
        )
        assert isinstance(pkg["topics"], list) and pkg["topics"], f"Package '{name}' must list topics"

