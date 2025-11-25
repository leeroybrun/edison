from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import yaml

# Resolve repository root that contains the Edison core
_CUR = Path(__file__).resolve()
REPO_ROOT: Path | None = None
for parent in _CUR.parents:
    if (parent / ".edison" / "core" / "lib" / "config.py").exists():
        REPO_ROOT = parent
        break
assert REPO_ROOT is not None, "cannot locate repository root with .edison/core present"

CORE_COMMANDS_PATH = REPO_ROOT / ".edison" / "core" / "config" / "commands.yaml"
PACK_COMMANDS_PATH = REPO_ROOT / ".edison" / "packs" / "typescript" / "config" / "commands.yml"
PROJECT_COMMANDS_PATH = REPO_ROOT / ".agents" / "config" / "commands.yml"
COMMANDS_SCHEMA_PATH = REPO_ROOT / ".edison" / "core" / "schemas" / "commands-config.schema.json"


def _load_yaml(path: Path) -> Dict[str, Any]:
    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _definitions_by_id(defs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {d["id"]: d for d in defs if "id" in d}


def _merge_selection(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    if "mode" in override:
        merged["mode"] = override["mode"]
    if "domains" in override:
        merged["domains"] = override["domains"]
    if "exclude" in override:
        base_ex = merged.get("exclude", []) or []
        over_ex = override.get("exclude", []) or []
        merged["exclude"] = list(dict.fromkeys([*base_ex, *over_ex]))
    return merged


def _merge_definitions(base: List[Dict[str, Any]], override: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = [deepcopy(item) for item in base]
    index = {item.get("id"): item for item in merged if "id" in item}
    for item in override:
        def_id = item.get("id")
        if not def_id:
            continue
        if def_id in index:
            index[def_id].update(item)
        else:
            copy = deepcopy(item)
            merged.append(copy)
            index[def_id] = copy
    return merged


def compose_command_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for cfg in configs:
        if not cfg:
            continue
        src = cfg.get("commands", {})
        dest = deepcopy(merged.get("commands", {}))

        # Simple scalar/dict keys
        for key, val in src.items():
            if key in {"definitions", "selection"}:
                continue
            dest[key] = deepcopy(val)

        # Selection merge (union excludes)
        base_sel = dest.get("selection", {})
        override_sel = src.get("selection", {})
        if base_sel or override_sel:
            dest["selection"] = _merge_selection(base_sel, override_sel)

        # Definition merge (by id)
        base_defs = dest.get("definitions", [])
        override_defs = src.get("definitions", [])
        dest["definitions"] = _merge_definitions(base_defs, override_defs)

        merged["commands"] = dest
    return merged


def test_load_core_config() -> None:
    cfg = _load_yaml(CORE_COMMANDS_PATH)
    commands = cfg.get("commands", {})
    defs = _definitions_by_id(commands.get("definitions", []))

    assert commands.get("enabled") is True
    assert {"claude", "cursor", "codex"} == set(commands.get("platforms", []))
    assert "session-next" in defs
    assert defs["session-next"]["cli"] == "edison session next"


def test_config_schema_validation() -> None:
    cfg = _load_yaml(CORE_COMMANDS_PATH)
    schema = yaml.safe_load(COMMANDS_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema)  # Construct to ensure schema validity
    jsonschema.validate(instance=cfg, schema=schema)


def test_short_desc_length() -> None:
    merged = compose_command_configs(
        _load_yaml(CORE_COMMANDS_PATH),
        _load_yaml(PACK_COMMANDS_PATH),
        _load_yaml(PROJECT_COMMANDS_PATH),
    )
    for item in merged["commands"]["definitions"]:
        desc = item.get("short_desc", "")
        assert len(desc) <= 120, f"short_desc too long for {item.get('id')}"


def test_required_fields() -> None:
    merged = compose_command_configs(
        _load_yaml(CORE_COMMANDS_PATH),
        _load_yaml(PACK_COMMANDS_PATH),
        _load_yaml(PROJECT_COMMANDS_PATH),
    )
    required = {"id", "domain", "command", "short_desc", "cli"}
    for item in merged["commands"]["definitions"]:
        missing = required - set(item.keys())
        assert not missing, f"{item.get('id')} missing required fields: {missing}"


def test_pack_extension_merge() -> None:
    composed = compose_command_configs(
        _load_yaml(CORE_COMMANDS_PATH),
        _load_yaml(PACK_COMMANDS_PATH),
    )
    defs = _definitions_by_id(composed["commands"]["definitions"])
    assert "session-next" in defs, "core command should remain after merge"
    assert "typescript-check" in defs, "typescript pack command should extend core definitions"
    assert defs["typescript-check"]["cli"] == "tsc --noEmit"


def test_project_override() -> None:
    composed = compose_command_configs(
        _load_yaml(CORE_COMMANDS_PATH),
        _load_yaml(PACK_COMMANDS_PATH),
        _load_yaml(PROJECT_COMMANDS_PATH),
    )
    defs = _definitions_by_id(composed["commands"]["definitions"])

    # Project override must update existing task-claim without dropping domain/cli
    task_claim = defs["task-claim"]
    assert task_claim["short_desc"] == "Claim project task"
    assert task_claim["domain"] == "task"
    assert "claim" == task_claim["command"]
    assert task_claim["cli"] == "edison task claim $1"

    # Selection exclusions must union core + project override
    selection = composed["commands"]["selection"]
    assert "validate-now" in selection.get("exclude", [])
    for base_exclude in ["setup", "internal", "migrate"]:
        assert base_exclude in selection.get("exclude", [])
