from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from edison.core.config import ConfigManager
from edison.data import get_data_path

# ROOT is determined by test fixtures for isolated testing
ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = get_data_path("config").parent  # Points to src/edison/data/

def test_deep_merge_basic_dict_and_arrays() -> None:
    mgr = ConfigManager(ROOT)
    base = {"a": {"x": 1, "y": [1, 2]}, "b": [1, 2, 3], "c": 1}
    override = {"a": {"y": ["+", 3, 4]}, "b": ["=", 9], "c": 2, "d": "new"}
    merged = mgr.deep_merge(base, override)
    assert merged["a"]["y"] == [1, 2, 3, 4]
    assert merged["b"] == [9]
    assert merged["c"] == 2
    assert merged["d"] == "new"


def test_env_overrides_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Use simple keys that match existing config to exercise
    # case-insensitive lookup without relying on complex splitting.
    monkeypatch.setenv("EDISON_tdd_enforceRedGreenRefactor", "false")
    monkeypatch.setenv("EDISON_tdd_requireEvidence", "false")

    mgr = ConfigManager(ROOT)
    base = mgr.load_yaml(mgr.core_defaults_path)
    assert base["tdd"]["enforceRedGreenRefactor"] is True
    assert base["tdd"]["requireEvidence"] is True

    mgr.apply_env_overrides(base, strict=True)
    assert base["tdd"]["enforceRedGreenRefactor"] is False
    assert base["tdd"]["requireEvidence"] is False


def test_load_and_validate_schema() -> None:
    mgr = ConfigManager(ROOT)
    cfg = mgr.load_config(validate=True)
    assert "validation" in cfg and "delegation" in cfg
    b = cfg.get("validation", {}).get("blocking_validators", [])  # type: ignore[assignment]
    assert isinstance(b, list) and len(b) >= 2


def test_loads_defaults_yaml_not_yml(tmp_path: Path) -> None:
    """ConfigManager must prefer config/defaults.yaml over config/defaults.yml."""
    # Arrange: isolated repo root with both .yaml and .yml present under core/config
    core_config_dir = tmp_path / ".edison" / "core" / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    (core_config_dir / "defaults.yaml").write_text("version: '2.0.0'\n", encoding="utf-8")
    (core_config_dir / "defaults.yml").write_text("version: '1.0.0'\n", encoding="utf-8")

    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    # Minimal project overlay required by ConfigManager; does not override version
    (project_config_dir / "project.yml").write_text("project: { name: test }\n", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    cfg = mgr.load_config(validate=False)

    # Should load version from defaults.yaml, ignoring defaults.yml
    assert cfg.get("version") == "2.0.0"


def test_load_config_uses_canonical_config_schema() -> None:
    """
    ConfigManager must default to validate=True and use config.schema.json
    as the canonical Draft-2020-12 schema for Edison configuration.
    """
    mgr = ConfigManager(ROOT)

    # API default must be validate=True so callers get validation by default.
    assert ConfigManager.load_config.__defaults__ == (True,)

    # Canonical schema path is bundled in edison.data
    schema_path = get_data_path("schemas", "config.schema.json")
    assert schema_path.exists(), "Canonical config schema missing"

    # Schema itself must be a valid Draft-2020-12 schema.
    import json
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_config_manager_defaults_to_project_root_not_edison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ConfigManager() without repo_root must resolve to the outer project root.

    This guards against treating the inner .edison git repo as the project root
    when running commands from within .edison/core.
    """
    # Import here to avoid affecting module-level imports.
    import edison.core.paths.resolver as resolver  # type: ignore

    # Simulate running inside the Edison framework directory.
    monkeypatch.chdir(CORE_ROOT)

    # Ensure no environment override and clear cached project root.
    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    resolver._PROJECT_ROOT_CACHE = None

    mgr = ConfigManager()

    # Repo root must be the outer project root, not .edison.
    assert mgr.repo_root == ROOT
    # And project config overlays must resolve from the outer preferred config directory.
    # Defaults to .edison/config now
    assert mgr.project_config_dir == ROOT / ".edison" / "config"


def test_legacy_core_defaults_yaml_outside_config_dir_is_ignored(tmp_path: Path) -> None:
    """Legacy .edison/core/defaults.yaml must not be used by ConfigManager."""
    # Legacy monolithic defaults at .edison/core/defaults.yaml (must be ignored)
    legacy_core_dir = tmp_path / ".edison" / "core"
    legacy_core_dir.mkdir(parents=True, exist_ok=True)
    (legacy_core_dir / "defaults.yaml").write_text("version: '0.9.0'\n", encoding="utf-8")

    # Canonical defaults under .edison/core/config/defaults.yaml
    core_config_dir = legacy_core_dir / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    (core_config_dir / "defaults.yaml").write_text("version: '2.1.0'\n", encoding="utf-8")

    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    (project_config_dir / "project.yml").write_text("project: { name: test }\n", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    cfg = mgr.load_config(validate=False)

    # Config MUST come from core/config/defaults.yaml, not legacy defaults.yaml.
    assert cfg.get("version") == "2.1.0"
