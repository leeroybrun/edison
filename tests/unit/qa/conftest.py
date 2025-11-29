"""Shared fixtures for QA evidence tests."""
from __future__ import annotations

from pathlib import Path
import subprocess
import shutil

import pytest
import yaml

from tests.helpers import create_round_dir


@pytest.fixture
def round_dir(tmp_path: Path) -> Path:
    """Create a round directory for testing."""
    return create_round_dir(tmp_path, 1)


@pytest.fixture
def isolated_qa_config(tmp_path: Path, monkeypatch) -> Path:
    """Create an isolated project with custom QA config."""
    # Set up isolated project root
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    # Initialize git repo (required by PathResolver)
    subprocess.run(
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
    edison_legacy_config = REPO_ROOT / ".edison" / "core" / "config"

    edison_core_config_src = edison_bundled_config if edison_bundled_config.exists() else edison_legacy_config
    edison_core_config_dst = tmp_path / ".edison" / "core" / "config"

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
                "bundleSummaryFile": "custom-bundle.json",
                "implementationReportFile": "custom-impl.json",
            }
        }
    }

    config_file = config_dir / "qa.yml"
    config_file.write_text(yaml.safe_dump(custom_config))

    # Clear ALL caches to pick up new config
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Also clear PathResolver cache to ensure it picks up the new root
    import edison.core.utils.paths.resolver as paths_resolver
    paths_resolver._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]

    return tmp_path
