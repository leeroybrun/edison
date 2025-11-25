from __future__ import annotations

from pathlib import Path
import sys

# Locate project root by walking upward until core config module is found.
_CUR = Path(__file__).resolve()
ROOT: Path | None = None
CORE_ROOT: Path | None = None

for cand in _CUR.parents:
    if (cand / ".edison" / "core" / "lib" / "config.py").exists():
        ROOT = cand
        CORE_ROOT = cand / ".edison" / "core"
        break

assert ROOT is not None, "Unable to locate project root for legacy-config checks"
assert CORE_ROOT is not None

from edison.core.config import ConfigManager  # type: ignore  # noqa: E402


def test_core_config_has_no_json_configs() -> None:
    """Core config must be YAML-only; schemas are the only JSON allowed."""
    cfg_dir = ROOT / ".edison" / "core" / "config"
    json_configs = [
        p for p in cfg_dir.rglob("*.json") if not p.name.endswith(".schema.json")
    ]
    assert not json_configs, f"Legacy JSON configs found in core: {json_configs}"


def test_project_overlays_use_yaml_only() -> None:
    """Project overlays must rely on YAML config; JSON configs are forbidden."""
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
        ROOT / ".edison" / "core" / "config" / "state-machine.yaml",
    ]
    missing = [p for p in required if not p.exists()]
    assert not missing, f"Expected YAML configs missing: {missing}"


def test_state_machine_available_from_yaml_only() -> None:
    """Session/task/QA state machines must be sourced from YAML config."""
    cfg = ConfigManager(ROOT).load_config(validate=False)
    sm = cfg.get("statemachine", {}) if isinstance(cfg, dict) else {}
    session_states = sm.get("session", {}).get("states", {}) if isinstance(sm, dict) else {}
    assert session_states, "Session state machine missing after JSON cleanup"
    for expected in ("draft", "active", "validated"):
        assert expected in session_states, f"Session state '{expected}' missing from YAML state machine"


def test_no_root_legacy_cache_dir() -> None:
    """Deprecated top-level .cache/composed must not linger."""
    legacy_cache = ROOT / ".cache" / "composed"
    assert not legacy_cache.exists(), "Legacy .cache/composed directory should be removed"
