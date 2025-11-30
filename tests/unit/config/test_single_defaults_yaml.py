from __future__ import annotations

from pathlib import Path

from edison.data import get_data_path
from tests.helpers.paths import get_repo_root


def test_only_one_defaults_yaml_exists() -> None:
    """There must be a single authoritative defaults.yaml in the repository."""
    root = get_repo_root()
    defaults_files = sorted(p.resolve() for p in root.rglob("defaults.yaml") if p.is_file())

    canonical = get_data_path("config", "defaults.yaml").resolve()

    assert canonical in defaults_files, f"Canonical defaults.yaml missing at {canonical}"
    assert defaults_files == [canonical], f"Found duplicate defaults.yaml files: {defaults_files}"
