from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict
import json

import jsonschema
import yaml

from edison.data import get_data_path

# Get paths to bundled Edison data
CORE_HOOKS_PATH = get_data_path("config", "hooks.yaml")
PACK_HOOKS_PATH = get_data_path("packs") / "typescript" / "config" / "hooks.yml"
SCHEMA_PATH = get_data_path("schemas", "hooks-config.schema.json")

# For project hooks, try to find the wilson-leadgen project, else skip
_CUR = Path(__file__).resolve()
PROJECT_ROOT: Path | None = None
for parent in _CUR.parents:
    if (parent / ".agents" / "config" / "hooks.yml").exists():
        PROJECT_ROOT = parent
        break

PROJECT_HOOKS_PATH = PROJECT_ROOT / ".agents" / "config" / "hooks.yml" if PROJECT_ROOT else None


def _load_yaml(path: Path) -> Dict[str, Any]:
    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = deepcopy(base)
    for key, val in override.items():
        if key == "id":
            continue
        if isinstance(merged.get(key), dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = deepcopy(val)
    return merged


def _merge_definitions(base: Dict[str, Any], override: Any) -> Dict[str, Any]:
    merged: Dict[str, Any] = {k: deepcopy(v) for k, v in (base or {}).items()}
    if isinstance(override, dict):
        for key, val in override.items():
            merged[key] = _deep_merge(merged.get(key, {}), val or {})
    elif isinstance(override, list):
        for item in override:
            if not isinstance(item, dict):
                continue
            def_id = item.get("id")
            if not def_id:
                continue
            merged[def_id] = _deep_merge(merged.get(def_id, {}), item)
    return merged


def compose_hook_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for cfg in configs:
        hooks_src = cfg.get("hooks", {})
        hooks_dest = deepcopy(merged.get("hooks", {}))

        # Simple keys (enabled/platforms/settings/etc.)
        for key, val in hooks_src.items():
            if key == "definitions":
                continue
            hooks_dest[key] = deepcopy(val)

        # Definitions merge (dict-based with optional list overrides)
        hooks_dest["definitions"] = _merge_definitions(
            hooks_dest.get("definitions", {}),
            hooks_src.get("definitions", {}),
        )

        merged["hooks"] = hooks_dest
    return merged


def test_load_core_config() -> None:
    cfg = _load_yaml(CORE_HOOKS_PATH)
    hooks = cfg.get("hooks", {})
    defs = hooks.get("definitions", {})

    assert hooks.get("enabled") is True
    assert hooks.get("platforms") == ["claude"]
    assert hooks.get("settings", {}).get("timeout_seconds") == 60
    assert "commit-guard" in defs and defs["commit-guard"]["blocking"] is True
    assert defs["inject-session-context"]["hook_type"] == "prompt"


def test_schema_validation() -> None:
    cfg = _load_yaml(CORE_HOOKS_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema)  # ensure schema is structurally valid
    jsonschema.validate(instance=cfg, schema=schema)


def test_all_hook_types_supported() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    enum_types = set(
        schema["properties"]["hooks"]["properties"]["definitions"]["patternProperties"][".*"]["properties"]["type"]["enum"]  # noqa: E501
    )
    expected = {
        "PreToolUse",
        "PostToolUse",
        "PermissionRequest",
        "UserPromptSubmit",
        "SessionStart",
        "SessionEnd",
        "Stop",
        "SubagentStop",
    }
    assert enum_types == expected


def test_blocking_only_for_pretooluse() -> None:
    configs = [_load_yaml(CORE_HOOKS_PATH), _load_yaml(PACK_HOOKS_PATH)]
    if PROJECT_HOOKS_PATH and PROJECT_HOOKS_PATH.exists():
        configs.append(_load_yaml(PROJECT_HOOKS_PATH))

    merged = compose_hook_configs(*configs)
    for defn in merged["hooks"]["definitions"].values():
        if defn.get("blocking") is True:
            assert defn.get("type") == "PreToolUse"


def test_matcher_required_for_tool_hooks() -> None:
    configs = [_load_yaml(CORE_HOOKS_PATH), _load_yaml(PACK_HOOKS_PATH)]
    if PROJECT_HOOKS_PATH and PROJECT_HOOKS_PATH.exists():
        configs.append(_load_yaml(PROJECT_HOOKS_PATH))

    merged = compose_hook_configs(*configs)
    for defn in merged["hooks"]["definitions"].values():
        if defn.get("type") in {"PreToolUse", "PostToolUse"}:
            matcher = defn.get("matcher")
            assert matcher and isinstance(matcher, str)


def test_pack_extension_merge() -> None:
    composed = compose_hook_configs(
        _load_yaml(CORE_HOOKS_PATH),
        _load_yaml(PACK_HOOKS_PATH),
    )
    defs = composed["hooks"]["definitions"]
    assert "inject-session-context" in defs
    assert "typescript-format" in defs
    assert defs["typescript-format"]["config"]["run_tsc_check"] is False


def test_project_override() -> None:
    if not PROJECT_HOOKS_PATH or not PROJECT_HOOKS_PATH.exists():
        import pytest
        pytest.skip("Project hooks.yml not found - test requires wilson-leadgen project")

    composed = compose_hook_configs(
        _load_yaml(CORE_HOOKS_PATH),
        _load_yaml(PACK_HOOKS_PATH),
        _load_yaml(PROJECT_HOOKS_PATH),
    )
    defs = composed["hooks"]["definitions"]
    assert defs["remind-tdd"]["enabled"] is False
    assert defs["commit-guard"]["config"]["coverage_threshold"] == 85
    assert defs["commit-guard"]["config"]["require_tests_pass"] is True
    assert defs["check-tests"]["enabled"] is True
