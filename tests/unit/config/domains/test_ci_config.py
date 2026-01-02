"""Tests for CI configuration domain.

TDD: Tests for CIConfig domain configuration.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
import yaml

from edison.core.config.cache import clear_all_caches


@pytest.fixture
def edison_project_with_ci(tmp_path: Path) -> Generator[Path, None, None]:
    """Create an Edison project with CI configuration."""
    clear_all_caches()

    # Create .git for valid repo
    (tmp_path / ".git").mkdir()

    # Create .edison config directory
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    config_dir = edison_dir / "config"
    config_dir.mkdir()

    # Create ci.yaml
    ci_config = {
        "ci": {
            "commands": {
                "type-check": "mypy src",
                "lint": "ruff check src",
                "test": "pytest tests -v",
                "build": "python -m build",
                # Null values should be filtered out
                "unused": None,
            },
        },
    }
    (config_dir / "ci.yaml").write_text(yaml.safe_dump(ci_config))

    yield tmp_path

    clear_all_caches()


class TestCIConfig:
    """Tests for CIConfig domain."""

    def test_ci_config_loads_commands(self, edison_project_with_ci: Path) -> None:
        """CIConfig should load commands from ci.yaml."""
        from edison.core.config.domains.ci import CIConfig

        config = CIConfig(repo_root=edison_project_with_ci)

        assert "type-check" in config.commands
        assert config.commands["type-check"] == "mypy src"

    def test_ci_config_filters_null_values(self, edison_project_with_ci: Path) -> None:
        """CIConfig should filter out null command values."""
        from edison.core.config.domains.ci import CIConfig

        config = CIConfig(repo_root=edison_project_with_ci)

        # "unused" was set to None and should be filtered out
        assert "unused" not in config.commands

    def test_ci_config_get_command(self, edison_project_with_ci: Path) -> None:
        """CIConfig.get_command should return specific command."""
        from edison.core.config.domains.ci import CIConfig

        config = CIConfig(repo_root=edison_project_with_ci)

        assert config.get_command("lint") == "ruff check src"
        assert config.get_command("nonexistent") is None

    def test_ci_config_get_command_required_raises(self, edison_project_with_ci: Path) -> None:
        """CIConfig.get_command_required should raise for missing command."""
        from edison.core.config.domains.ci import CIConfig

        config = CIConfig(repo_root=edison_project_with_ci)

        with pytest.raises(RuntimeError, match="not configured"):
            config.get_command_required("nonexistent")

    def test_ci_config_list_commands(self, edison_project_with_ci: Path) -> None:
        """CIConfig.list_commands should return all command names."""
        from edison.core.config.domains.ci import CIConfig

        config = CIConfig(repo_root=edison_project_with_ci)

        names = config.list_commands()

        assert "type-check" in names
        assert "lint" in names
        assert "test" in names
        assert "build" in names
        # Null value should be filtered
        assert "unused" not in names
