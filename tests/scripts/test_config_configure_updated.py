"""Tests for the interactive Edison configuration menu (configure.py).

These tests use real temp directories (no mocks) to ensure the menu loads and
persists configuration safely while discovering options dynamically from
setup.yaml.

UPDATED: Tests now use modular config/*.yml structure instead of monolithic config.yml

DEPRECATED: These tests reference scripts/config/configure.py which was removed
during the uvx migration. The functionality moved to edison.cli.config.configure
but with different implementation. Tests need rewrite when TUI is reimplemented.
"""

from __future__ import annotations

import os
from pathlib import Path
import importlib.util
import sys
import yaml

import pytest

pytestmark = pytest.mark.skip(reason="Legacy scripts/config/configure.py removed during uvx migration. Rewrite needed for new CLI.")


# Paths relative to this test file
CORE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = CORE_DIR.parent.parent


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _load_configure_module():
    spec = importlib.util.spec_from_file_location(
        "edison_configure", CORE_DIR / "scripts" / "config" / "configure.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_discovery_fixtures(root: Path) -> None:
    """Create minimal discovery inputs under the isolated repo root."""

    # Packs
    _write_yaml(root / ".edison/packs/alpha/config.yml", {"id": "alpha"})
    _write_yaml(root / ".edison/packs/beta/config.yml", {"id": "beta"})

    # Validators and agents (core discovery paths)
    _write_yaml(
        root / ".edison/core/config/validators.yaml",
        {"validators": [{"id": "lint"}, {"id": "security"}]},
    )
    _write_yaml(
        root / ".edison/core/config/agents.yaml",
        {"agents": [{"id": "builder"}, {"id": "reviewer"}]},
    )


def test_menu_loads_current_config(isolated_project_env, tmp_path: Path):
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    # Use modular config structure
    cfg_path = tmp_path / ".agents" / "config" / "defaults.yml"
    _write_yaml(cfg_path, {"project": {"name": "demo-app"}})

    menu = ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    assert menu.current_config.get("project", {}).get("name") == "demo-app"


def test_discovers_dynamic_options(isolated_project_env, tmp_path: Path):
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    _make_discovery_fixtures(tmp_path)

    menu = ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    options = menu.available_options
    assert set(options.get("packs", [])) >= {"alpha", "beta"}
    assert set(options.get("validators", [])) >= {"lint", "security"}
    assert set(options.get("agents", [])) >= {"builder", "reviewer"}
    # Orchestrators fall back to values defined in setup.yaml
    assert "claude" in options.get("orchestrators", [])


def test_tracks_and_saves_changes(isolated_project_env, tmp_path: Path):
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    # Create modular config files
    config_dir = tmp_path / ".agents" / "config"
    _write_yaml(config_dir / "defaults.yml", {"project": {"name": "old"}})
    _write_yaml(config_dir / "tdd.yml", {"tdd": {"enforcement": "warn"}})

    menu = ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")
    menu.set_value("project_name", "new-name")
    menu.set_value("tdd_enforcement", "strict")

    # Changes tracked using dotted keys
    assert menu.changes.get("project.name") == "new-name"
    assert menu.changes.get("tdd.enforcement") == "strict"

    # Persist and verify backup + updated values
    exit_code = menu.save_changes(dry_run=False)
    assert exit_code == 0

    # Check modular files
    saved_defaults = yaml.safe_load((config_dir / "defaults.yml").read_text())
    assert saved_defaults["project"]["name"] == "new-name"

    saved_tdd = yaml.safe_load((config_dir / "tdd.yml").read_text())
    assert saved_tdd["tdd"]["enforcement"] == "strict"

    # Check backups
    assert (config_dir / "defaults.yml.bak").exists()
    backup_defaults = yaml.safe_load((config_dir / "defaults.yml.bak").read_text())
    assert backup_defaults["project"]["name"] == "old"


def test_dry_run_does_not_write(isolated_project_env, tmp_path: Path):
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    cfg_path = tmp_path / ".agents" / "config" / "defaults.yml"
    _write_yaml(cfg_path, {"project": {"name": "alpha"}})

    menu = ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")
    menu.set_value("project_name", "beta")

    exit_code = menu.save_changes(dry_run=True)
    assert exit_code == 0

    saved = yaml.safe_load(cfg_path.read_text())
    assert saved["project"]["name"] == "alpha"
    assert not cfg_path.with_suffix(".yml.bak").exists()


def test_validation_blocks_invalid_values(isolated_project_env, tmp_path: Path):
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    cfg_path = tmp_path / ".agents" / "config" / "tdd.yml"
    _write_yaml(cfg_path, {"tdd": {"coverage_threshold": 50}})

    menu = ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    with pytest.raises(ValueError):
        menu.set_value("coverage_threshold", 150)  # exceeds 0-100 range defined in setup.yaml


def test_simple_mode_without_prompt_toolkit(isolated_project_env, tmp_path: Path):
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    cfg_path = tmp_path / ".agents" / "config" / "defaults.yml"
    _write_yaml(cfg_path, {"project": {"name": "demo"}})

    menu = ConfigurationMenu(
        repo_root=tmp_path,
        edison_core=CORE_DIR,
        config_dir=".agents",
        force_simple=True,
    )

    # Non-interactive run returns quickly without installing prompt_toolkit
    exit_code = menu.run(dry_run=True, non_interactive=True)
    assert exit_code == 0


def test_migrates_legacy_config_yml(isolated_project_env, tmp_path: Path):
    """Test that legacy config.yml is automatically migrated to modular config/."""
    ConfigurationMenu = _load_configure_module().ConfigurationMenu

    # Create OLD monolithic config.yml
    legacy_path = tmp_path / ".agents" / "config.yml"
    _write_yaml(legacy_path, {
        "project": {"name": "old-project", "custom": "preserve-me"},
        "tdd": {"enforcement": "warn", "custom_tdd": "keep-this"},
        "ci": {"commands": {"lint": "pnpm lint"}}
    })

    menu = ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")
    menu.set_value("project_name", "migrated-project")

    # Save should trigger migration
    exit_code = menu.save_changes(dry_run=False)
    assert exit_code == 0

    # Legacy file should be gone
    assert not legacy_path.exists()

    # Backup should exist
    assert (legacy_path.with_suffix(".yml.legacy.bak")).exists()

    # Modular files should be created
    config_dir = tmp_path / ".agents" / "config"
    assert (config_dir / "defaults.yml").exists()
    assert (config_dir / "tdd.yml").exists()
    assert (config_dir / "ci.yml").exists()

    # Custom fields should be preserved
    defaults = yaml.safe_load((config_dir / "defaults.yml").read_text())
    assert defaults["project"]["name"] == "migrated-project"
    assert defaults["project"]["custom"] == "preserve-me"

    tdd = yaml.safe_load((config_dir / "tdd.yml").read_text())
    assert tdd["tdd"]["custom_tdd"] == "keep-this"
