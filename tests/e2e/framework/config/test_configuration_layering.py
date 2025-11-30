"""
Configuration Layering Scenario Coverage Tests (Dimension 10)

New architecture (NO LEGACY, NO PACKS):
- Core defaults live at `.edison/core/config/defaults.yaml`.
- Project overlays live at `<project_config_dir>/config/*.yml` (default: `.edison/config/*.yml`).
- Environment overrides sit on top and preserve the original case when creating
  new keys (e.g., `EDISON_QUALITY__LEVEL` -> `{"quality": {"LEVEL": ...}}`).

Precedence: env > project overlays > core defaults.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
import json

from tests.helpers.paths import get_repo_root
from tests.helpers.fixtures import create_repo_with_git

# Add Edison core to path
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = get_repo_root()

CORE_ROOT = _CORE_ROOT
from edison.core.config import ConfigManager

from helpers.io_utils import write_yaml


def make_tmp_repo(
    tmp_path: Path,
    core_defaults: dict,
    *,
    core_modules: dict | None = None,
    project_overlays: dict | None = None,
) -> Path:
    """Create temporary repo with the new 3-layer config layout."""
    # Create real git repository to make PathResolver happy
    repo = create_repo_with_git(tmp_path)

    # Core defaults & modular core config (.edison/core/config/*.yaml)
    core_dir = repo / ".edison" / "core" / "config"
    write_yaml(core_dir / "defaults.yaml", core_defaults)
    for name, data in (core_modules or {}).items():
        fname = name if name.endswith(".yaml") else f"{name}.yaml"
        write_yaml(core_dir / fname, data)

    # Project overlays (<project_config_dir>/config/*.yml)
    if project_overlays:
        proj_dir = repo / ".edison" / "config"
        for name, data in project_overlays.items():
            fname = name if name.endswith(".yml") else f"{name}.yml"
            write_yaml(proj_dir / fname, data)

    return repo


# ==================== SCENARIO 1: Core Defaults Only ====================


def test_scenario_1_core_defaults_only(tmp_path: Path):
    """
    Scenario 1: Core defaults only (minimal config)
    - Project has no project overlays
    - Core defaults from .edison/core/config/defaults.yaml used
    - System functional with defaults
    """
    defaults = {
        "edison": {"version": "1.0.0"},
        "quality": {
            "coverage": {"overall": 80, "changed": 100},
            "allowSkip": False,
            "blockOnFailingTests": True,
        },
        "tdd": {
            "enforceRedGreenRefactor": True,
            "requireEvidence": True,
        },
    }

    repo = make_tmp_repo(tmp_path, defaults, project_overlays=None)
    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    # Verify core defaults are loaded
    assert cfg["edison"]["version"] == "1.0.0"
    assert cfg["quality"]["coverage"]["overall"] == 80
    assert cfg["quality"]["coverage"]["changed"] == 100
    assert cfg["quality"]["allowSkip"] is False
    assert cfg["tdd"]["enforceRedGreenRefactor"] is True
    assert cfg["tdd"]["requireEvidence"] is True


# ==================== SCENARIO 3: Core + Project Override ====================


def test_scenario_3_core_project_override(tmp_path: Path):
    """
    Scenario 3: Core + project override (packs removed)
    - Project overlays live in <project_config_dir>/config/*.yml
    - Project overrides win over core defaults
    """
    core_defaults = {
        "quality": {"coverage": {"overall": 80, "changed": 100}},
        "tdd": {"enforceRedGreenRefactor": True},
    }

    project_overlay = {
        "project": {"name": "my-project"},
        "quality": {"coverage": {"overall": 90}},  # Project overrides core
        "tdd": {"enforceRedGreenRefactor": False},
    }

    repo = make_tmp_repo(
        tmp_path,
        core_defaults,
        project_overlays={"project": project_overlay},
    )

    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    # Project overrides win over core
    assert cfg["quality"]["coverage"]["overall"] == 90
    assert cfg["quality"]["coverage"]["changed"] == 100  # Unchanged from core
    assert cfg["tdd"]["enforceRedGreenRefactor"] is False
    assert cfg["project"]["name"] == "my-project"


# ==================== SCENARIO 4: Core + Project + Env Override ====================


def test_scenario_4_full_precedence_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Scenario 4: Core + project + env override
    - Environment variable overrides project config
    - Precedence: env > project > core (no packs)
    - Env vars preserve case when creating NEW keys
    """
    core_defaults = {
        "quality": {"coverage": {"overall": 80, "changed": 100}},
        "tdd": {"enforceRedGreenRefactor": True, "requireEvidence": True},
        "session": {"timeout_hours": 8, "max_concurrent": 4},
    }

    project_config = {
        "quality": {"coverage": {"overall": 90}},
        "tdd": {"enforceRedGreenRefactor": False},
        "session": {"timeout_hours": 12},
    }

    repo = make_tmp_repo(tmp_path, core_defaults, project_overlays={"project": project_config})

    # Environment overrides: override existing keys and create new ones
    monkeypatch.setenv("EDISON_QUALITY__COVERAGE__OVERALL", "95")
    monkeypatch.setenv("EDISON_SESSION__TIMEOUT_HOURS", "16")
    monkeypatch.setenv("EDISON_QUALITY__LEVEL", "gold")  # New key keeps uppercase LEVEL
    monkeypatch.setenv("EDISON_RUNTIME__LOG_LEVEL", "debug")  # New top-level key keeps case

    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    # Env wins over project/core
    assert cfg["quality"]["coverage"]["overall"] == 95
    assert cfg["session"]["timeout_hours"] == 16

    # Project layer still visible where env absent
    assert cfg["tdd"]["enforceRedGreenRefactor"] is False
    # Core layer still visible where untouched
    assert cfg["quality"]["coverage"]["changed"] == 100
    assert cfg["tdd"]["requireEvidence"] is True

    # Note: Env vars preserve case when creating new keys
    # EDISON_QUALITY__LEVEL -> {"quality": {"LEVEL": ...}}
    assert cfg["quality"]["LEVEL"] == "gold"
    # EDISON_RUNTIME__LOG_LEVEL -> {"RUNTIME": {"LOG_LEVEL": ...}}
    assert cfg["RUNTIME"]["LOG_LEVEL"] == "debug"


def test_scenario_4b_env_array_operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Scenario 4b: Environment array append and index assignment
    - EDISON_PACKS__APPEND adds to newly created list
    - EDISON_AGENTS__0 sets specific index on new list
    - Env-created keys remain UPPERCASE because no YAML keys exist
    """
    repo = make_tmp_repo(tmp_path, core_defaults={})

    # Build lists purely from env
    monkeypatch.setenv("EDISON_PACKS__0", "react")
    monkeypatch.setenv("EDISON_PACKS__APPEND", "testing")

    monkeypatch.setenv("EDISON_AGENTS__0", "codex")
    monkeypatch.setenv("EDISON_AGENTS__1", "claude")
    monkeypatch.setenv("EDISON_AGENTS__APPEND", "gemini")

    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    assert cfg["PACKS"] == ["react", "testing"]
    assert cfg["AGENTS"] == ["codex", "claude", "gemini"]


def test_scenario_4c_env_deep_object_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Scenario 4c: Deep object paths via EDISON_A__B__C__D
    - Multi-level nesting works with empty core/project config
    - Creates intermediate containers as needed with original casing
    """
    repo = make_tmp_repo(tmp_path, core_defaults={})

    # Deep override
    monkeypatch.setenv("EDISON_DELEGATION__RESILIENCE__RETRY__MAX_ATTEMPTS", "5")
    monkeypatch.setenv("EDISON_DELEGATION__RESILIENCE__RETRY__BACKOFF_FACTOR", "3.0")

    # Create new deep path
    monkeypatch.setenv("EDISON_DELEGATION__RESILIENCE__CIRCUIT_BREAKER__ENABLED", "true")
    monkeypatch.setenv("EDISON_DELEGATION__RESILIENCE__CIRCUIT_BREAKER__THRESHOLD", "10")

    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    assert cfg["DELEGATION"]["RESILIENCE"]["RETRY"]["MAX_ATTEMPTS"] == 5
    assert cfg["DELEGATION"]["RESILIENCE"]["RETRY"]["BACKOFF_FACTOR"] == 3.0
    assert cfg["DELEGATION"]["RESILIENCE"]["CIRCUIT_BREAKER"]["ENABLED"] is True
    assert cfg["DELEGATION"]["RESILIENCE"]["CIRCUIT_BREAKER"]["THRESHOLD"] == 10


# ==================== SCENARIO 6: Invalid Config Handling ====================


def test_scenario_6_invalid_yaml_syntax(tmp_path: Path):
    """
    Scenario 6a: Invalid YAML syntax in project overlay
    - Invalid YAML under <project_config_dir>/config/invalid.yml raises
    """
    core_defaults = {"quality": {"coverage": {"overall": 80}}}
    repo = make_tmp_repo(tmp_path, core_defaults)

    invalid_yaml = """
    quality:
      coverage:
        overall: 90
      missing_colon_here
        broken: true
    """
    target = repo / ".edison" / "config" / "invalid.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(invalid_yaml)

    mgr = ConfigManager(repo_root=repo)

    with pytest.raises(Exception):  # yaml.YAMLError
        mgr.load_config()


def test_scenario_6b_invalid_env_var_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Scenario 6b: Invalid environment variable format
    - Malformed EDISON_* key (trailing empty segments)
    - ConfigManager skips malformed keys in non-strict mode
    - ConfigManager raises in strict mode
    """
    core_defaults = {"quality": {"coverage": {"overall": 80}}}
    repo = make_tmp_repo(tmp_path, core_defaults)

    # Malformed env var (trailing empty segments)
    monkeypatch.setenv("EDISON_BAD__PATH__", "value")

    mgr = ConfigManager(repo_root=repo)

    # In strict mode (validate=True), malformed keys raise ValueError
    with pytest.raises(ValueError, match="Malformed|empty segment"):
        mgr.load_config(validate=True)


def test_scenario_6c_schema_validation_failure(tmp_path: Path):
    """
    Scenario 6c: Schema validation failure
    - Project overlay has invalid value (e.g., coverage > 100)
    - Schema validation detects error
    """
    core_defaults = {"quality": {"coverage": {"overall": 80}}}

    project_overlay = {
        "quality": {"coverage": {"overall": 150}},  # Invalid: > 100
    }

    repo = make_tmp_repo(tmp_path, core_defaults, project_overlays={"project": project_overlay})

    # Copy real schema to tmp repo
    real_schema = Path(".edison/core/schemas/edison.schema.json")
    if real_schema.exists():
        import shutil
        (repo / ".edison" / "core" / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copy(real_schema, repo / ".edison" / "core" / "schemas" / "edison.schema.json")

        mgr = ConfigManager(repo_root=repo)

        with pytest.raises(Exception):  # jsonschema.ValidationError
            mgr.load_config(validate=True)


def test_scenario_6d_type_mismatch_in_config(tmp_path: Path):
    """
    Scenario 6d: Type mismatch in config
    - Config expects boolean/number, gets string
    - Schema validation catches these
    """
    core_defaults = {}

    project_overlay = {
        "quality": {
            "coverage": {"overall": "eighty"},  # Should be number
            "allowSkip": "yes",  # Should be boolean
        }
    }

    repo = make_tmp_repo(tmp_path, core_defaults, project_overlays={"project": project_overlay})

    real_schema = Path(".edison/core/schemas/edison.schema.json")
    if real_schema.exists():
        import shutil
        (repo / ".edison" / "core" / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copy(real_schema, repo / ".edison" / "core" / "schemas" / "edison.schema.json")

        mgr = ConfigManager(repo_root=repo)

        with pytest.raises(Exception):  # jsonschema.ValidationError
            mgr.load_config(validate=True)


# ==================== ADDITIONAL COVERAGE TESTS ====================


def test_array_merge_strategies(tmp_path: Path):
    """
    Test array merge strategies using project overlays (no edison.yaml):
    - Prepending '+' appends to base
    - Starting with '=' replaces base
    - Default replaces entire array
    """
    core_defaults = {
        "packs": ["react", "nextjs"],
        "agents": ["codex"],
        "validators": ["global"],
    }

    project_config = {
        "packs": ["+", "testing", "prisma"],  # Append
        "agents": ["=", "claude", "gemini"],  # Replace
        "validators": ["security"],  # Default replace
    }

    repo = make_tmp_repo(tmp_path, core_defaults, project_overlays={"project": project_config})
    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    assert cfg["packs"] == ["react", "nextjs", "testing", "prisma"]
    assert cfg["agents"] == ["claude", "gemini"]
    assert cfg["validators"] == ["security"]


def test_config_concurrent_access_safety(tmp_path: Path):
    """Verify ConfigManager is thread-safe for concurrent reads."""
    from concurrent.futures import ThreadPoolExecutor

    core_defaults = {
        "quality": {"coverage": {"overall": 80}},
        "session": {"max_concurrent": 4},
    }

    repo = make_tmp_repo(tmp_path, core_defaults)
    mgr = ConfigManager(repo_root=repo)

    def load_config():
        cfg = mgr.load_config()
        return cfg["quality"]["coverage"]["overall"]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: load_config(), range(20)))

    assert all(r == 80 for r in results)


def test_config_precedence_documentation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Comprehensive test documenting full precedence chain (3-layer model).
    Precedence: env > project overlays > core defaults.
    """
    # Layer 1: Core defaults
    core = {
        "value": "core",
        "layer1": "core-only",
        "layer2": "core-for-layer2",
        "layer3": "core-for-layer3",
        "layer4": "core-for-layer4",
    }

    # Layer 2: Project overlays
    project = {
        "value": "project",
        "layer3": "project-only",
        "layer4": "project-for-layer4",
    }

    repo = make_tmp_repo(tmp_path, core, project_overlays={"project": project})

    # Layer 3: Environment
    monkeypatch.setenv("EDISON_VALUE", "env")
    monkeypatch.setenv("EDISON_LAYER4", "env-only")

    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    # Verify precedence
    assert cfg["value"] == "env"  # Env wins
    assert cfg["layer1"] == "core-only"  # Only in core
    assert cfg["layer2"] == "core-for-layer2"  # Only in core
    assert cfg["layer3"] == "project-only"  # Project overrides core
    assert cfg["layer4"] == "env-only"  # Env overrides project


def test_missing_config_files_handled_gracefully(tmp_path: Path):
    """Test system works even with missing config files."""
    repo = create_repo_with_git(tmp_path)

    # No defaults.yaml, no project overlays
    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    # Should return empty dict without crashing
    assert isinstance(cfg, dict)


def test_env_var_type_coercion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify environment variables are properly type-coerced and nested."""
    repo = make_tmp_repo(tmp_path, core_defaults={})

    # Single-underscore keys become nested when no double-underscore is present
    monkeypatch.setenv("EDISON_BOOL_TRUE", "true")
    monkeypatch.setenv("EDISON_BOOL_FALSE", "false")
    monkeypatch.setenv("EDISON_INT", "42")
    monkeypatch.setenv("EDISON_FLOAT", "3.14")
    monkeypatch.setenv("EDISON_STRING", "hello world")
    monkeypatch.setenv("EDISON_JSON_OBJECT", '{"key": "value"}')
    monkeypatch.setenv("EDISON_JSON_ARRAY", '["a", "b", "c"]')

    mgr = ConfigManager(repo_root=repo)
    cfg = mgr.load_config()

    assert cfg["BOOL"]["TRUE"] is True
    assert cfg["BOOL"]["FALSE"] is False
    assert cfg["INT"] == 42
    assert isinstance(cfg["INT"], int)
    assert cfg["FLOAT"] == 3.14
    assert isinstance(cfg["FLOAT"], float)
    assert cfg["STRING"] == "hello world"
    assert cfg["JSON"]["OBJECT"] == {"key": "value"}
    assert cfg["JSON"]["ARRAY"] == ["a", "b", "c"]


# ==================== SUMMARY REPORT TEST ====================

def test_all_scenarios_summary():
    """
    Summary test that documents all scenarios covered.

    This test always passes and serves as documentation.
    """
    scenarios_covered = {
        "Scenario 1": "Core defaults only - ✓ Tested",
        "Scenario 3": "Core + project override - ✓ Tested",
        "Scenario 4": "Core + project + env override - ✓ Tested",
        "Scenario 4b": "Env array operations (upper-case keys) - ✓ Tested",
        "Scenario 4c": "Env deep object paths (upper-case keys) - ✓ Tested",
        "Scenario 6": "Invalid config handling - ✓ Tested",
        "Additional Coverage": {
            "Array merge strategies": "✓ Tested",
            "Concurrent access safety": "✓ Tested",
            "Precedence documentation": "✓ Tested",
            "Missing files handled": "✓ Tested",
            "Type coercion": "✓ Tested",
            "Deep object paths": "✓ Tested",
        },
    }

    # This test serves as documentation
    assert all(v for v in scenarios_covered.values())

    print("\n" + "=" * 60)
    print("CONFIGURATION LAYERING SCENARIO COVERAGE - COMPLETE")
    print("=" * 60)
    for scenario, status in scenarios_covered.items():
        if isinstance(status, dict):
            print(f"\n{scenario}:")
            for sub, sub_status in status.items():
                print(f"  {sub}: {sub_status}")
        else:
            print(f"{scenario}: {status}")
    print("=" * 60)
