from __future__ import annotations

from pathlib import Path
import sys
import pytest

from edison.core.config import ConfigManager
from edison.data import get_data_path

# Try to find wilson-leadgen project for legacy config checks
_CUR = Path(__file__).resolve()
ROOT: Path | None = None

for cand in _CUR.parents:
    if (cand / ".agents" / "config").exists():
        ROOT = cand
        break


def test_core_config_has_no_json_configs() -> None:
    """Core config must be YAML-only; schemas are the only JSON allowed."""
    # Check bundled Edison data
    cfg_dir = get_data_path("config")
    json_configs = [
        p for p in cfg_dir.rglob("*.json") if not p.name.endswith(".schema.json")
    ]
    assert not json_configs, f"Legacy JSON configs found in core: {json_configs}"


def test_project_overlays_use_yaml_only() -> None:
    """Project overlays must rely on YAML config; JSON configs are forbidden."""
    if not ROOT:
        pytest.skip("wilson-leadgen project not found - test requires project environment")

    forbidden = [
        ROOT / ".agents" / "delegation" / "config.json",
        ROOT / ".agents" / "validators" / "config.json",
        ROOT / ".agents" / "session-workflow.json",
        ROOT / ".edison" / ".agents" / "sessions" / "TEMPLATE.json",
    ]
    present = [p for p in forbidden if p.exists()]
    assert not present, f"Legacy project JSON configs still present: {present}"

    required = [
        ROOT / ".agents" / "config" / "delegation.yml",
        ROOT / ".agents" / "config" / "validators.yml",
    ]
    # State machine config should exist in bundled Edison config
    state_machine_config = get_data_path("config", "state-machine.yaml")
    assert state_machine_config.exists(), f"Bundled state-machine.yaml not found at {state_machine_config}"

    missing = [p for p in required if not p.exists()]
    assert not missing, f"Expected YAML configs missing: {missing}"


def test_state_machine_available_from_yaml_only() -> None:
    """Session/task/QA state machines must be sourced from YAML config."""
    if not ROOT:
        pytest.skip("wilson-leadgen project not found - test requires project environment")

    cfg = ConfigManager(ROOT).load_config(validate=False)
    sm = cfg.get("statemachine", {}) if isinstance(cfg, dict) else {}
    session_states = sm.get("session", {}).get("states", {}) if isinstance(sm, dict) else {}
    assert session_states, "Session state machine missing after JSON cleanup"
    for expected in ("draft", "active", "validated"):
        assert expected in session_states, f"Session state '{expected}' missing from YAML state machine"


def test_no_root_legacy_cache_dir() -> None:
    """Deprecated top-level .cache/composed must not linger."""
    if not ROOT:
        pytest.skip("wilson-leadgen project not found - test requires project environment")

    legacy_cache = ROOT / ".cache" / "composed"
    assert not legacy_cache.exists(), "Legacy .cache/composed directory should be removed"
