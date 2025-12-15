"""Shared fixtures for QA evidence tests."""
from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from tests.helpers import create_round_dir
from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.env_setup import setup_project_root
from edison.core.utils.subprocess import run_with_timeout


@pytest.fixture
def round_dir(tmp_path: Path) -> Path:
    """Create a round directory for testing."""
    return create_round_dir(tmp_path, 1)


@pytest.fixture
def isolated_qa_config(tmp_path: Path, monkeypatch) -> Path:
    """Create an isolated project with custom QA config.

    Uses centralized cache_utils for cache reset (DRY principle).
    """
    import subprocess

    # Reset caches before setup
    reset_edison_caches()

    # Set up isolated project root
    setup_project_root(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)

    # Initialize git repo (required by PathResolver)
    run_with_timeout(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Copy Edison core config files (like isolated_project_env does)
    from edison.core.utils.paths.resolver import PathResolver
    REPO_ROOT = PathResolver.resolve_project_root()
    edison_bundled_config = Path(__file__).parent.parent.parent.parent / "src" / "edison" / "data" / "config"
    edison_legacy_config = REPO_ROOT / ".edison" / "config"

    edison_core_config_src = edison_bundled_config if edison_bundled_config.exists() else edison_legacy_config
    edison_core_config_dst = tmp_path / ".edison" / "config"

    if edison_core_config_src.exists():
        edison_core_config_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(edison_core_config_src, edison_core_config_dst, dirs_exist_ok=True)

    # Create project-specific config directory
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create custom config with custom filenames
    # artifactPaths is under validation: in the YAML structure
    custom_config = {
        "validation": {
            "artifactPaths": {
                "bundleSummaryFile": "custom-bundle.md",
                "implementationReportFile": "custom-impl.md",
            }
        }
    }

    config_file = config_dir / "qa.yaml"
    config_file.write_text(yaml.safe_dump(custom_config))

    # Use centralized cache reset (includes all caches)
    reset_edison_caches()

    return tmp_path
