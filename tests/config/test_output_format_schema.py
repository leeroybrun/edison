from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from edison.data import get_data_path

OUTPUT_FORMAT_CONFIG_PATH = get_data_path("config", "output_format.yaml")
VALIDATOR_OUTPUT_DOC_PATH = get_data_path("guidelines", "validators/OUTPUT_FORMAT.md")
DELEGATION_SCHEMA_PATH = get_data_path("schemas", "delegation-report.schema.json")

EXPECTED_FOLLOWUP_FIELDS = {
    "title",
    "description",
    "type",
    "severity",
    "blocking",
    "claimNow",
    "parentId",
    "files",
    "suggestedSlug",
    "suggestedWave",
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_json(path: Path) -> Dict[str, Any]:
    assert path.exists(), f"missing schema file: {path}"
    return json.loads(path.read_text(encoding="utf-8")) or {}


def _extract_suggested_followups(config: Dict[str, Any]) -> Dict[str, Any]:
    validation = config.get("validationReport", {})
    schema = validation.get("suggestedFollowups")
    assert schema, "validationReport.suggestedFollowups schema must be defined"
    return schema


def test_output_format_config_restores_full_followup_schema() -> None:
    cfg = _load_yaml(OUTPUT_FORMAT_CONFIG_PATH)
    suggested_followups = _extract_suggested_followups(cfg)

    assert suggested_followups.get("type") == "array"
    items = suggested_followups.get("items", {})
    required = set(items.get("required", []))
    assert required == {"title", "description", "severity"}

    props = items.get("properties", {})
    missing = EXPECTED_FOLLOWUP_FIELDS - set(props.keys())
    assert not missing, f"Missing follow-up properties: {missing}"

    severity_enum = set(props["severity"].get("enum", []))
    assert severity_enum == {"critical", "high", "medium", "low"}

    type_enum = set(props["type"].get("enum", []))
    assert type_enum == {"bug", "enhancement", "refactor", "test", "docs"}

    assert props["blocking"].get("default") is False
    assert props["claimNow"].get("default") is False

    file_items = props["files"].get("items", {})
    assert file_items.get("type") == "string"

    assert props["suggestedWave"].get("type") == "integer"


def test_validator_output_format_doc_lists_full_followup_fields() -> None:
    text = VALIDATOR_OUTPUT_DOC_PATH.read_text(encoding="utf-8")
    assert "suggestedFollowups" in text, "Validator OUTPUT_FORMAT must document suggestedFollowups"
    for field in EXPECTED_FOLLOWUP_FIELDS:
        assert field in text, f"Validator OUTPUT_FORMAT must describe '{field}'"


def test_delegation_schema_aligns_with_config_followups() -> None:
    cfg = _extract_suggested_followups(_load_yaml(OUTPUT_FORMAT_CONFIG_PATH))
    cfg_items = cfg.get("items", {})
    cfg_props = cfg_items.get("properties", {})

    schema = _load_json(DELEGATION_SCHEMA_PATH)
    followups_schema = schema.get("properties", {}).get("suggestedFollowups", {})
    items = followups_schema.get("items", {})
    props = items.get("properties", {})

    assert set(items.get("required", [])) == set(cfg_items.get("required", []))
    assert set(props.keys()) == set(cfg_props.keys())

    assert props.get("suggestedWave", {}).get("type") == cfg_props.get("suggestedWave", {}).get("type")
    assert set(props.get("severity", {}).get("enum", [])) == set(cfg_props.get("severity", {}).get("enum", []))
    assert set(props.get("type", {}).get("enum", [])) == set(cfg_props.get("type", {}).get("enum", []))
