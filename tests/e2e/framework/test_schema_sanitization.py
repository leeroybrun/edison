from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


CORE = Path(".edison/core/schemas")
PROJECT = Path(".agents/schemas")


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_core_schemas_exist():
    expected = {
        "session.schema.json",
        "task.schema.json",
        "qa.schema.json",
        "config.schema.json",
        "delegation.schema.json",
        "manifest.schema.json",
    }
    assert CORE.exists(), "Core schemas directory missing: .edison/core/schemas"
    present = {p.name for p in CORE.glob("*.schema.json")}
    missing = sorted(expected - present)
    assert not missing, f"Missing core schemas: {missing}"


def test_no_legacy_edison_config_schemas():
    """
    There must be a single canonical config schema (config.schema.json).

    Legacy Draft-07 config schemas (edison.schema.json, edison-config.schema.json)
    should be removed or folded into the canonical Draft-2020-12 schema.
    """
    legacy = sorted(
        p.name
        for p in CORE.glob("edison*.schema.json")
        if p.name != "edison-task.schema.json"  # future-proof if added
    )
    assert not legacy, (
        "Legacy Edison config schemas should be removed or aliased via config.schema.json; "
        f"found: {legacy}"
    )


def test_core_schemas_valid_json_and_have_schema_decl():
    for path in sorted(CORE.glob("*.schema.json")):
        data = _read_json(path)
        assert "$schema" in data, f"$schema missing in {path}"
        # Validate meta-schema structure is acceptable
        Draft202012Validator.check_schema(data)


def test_core_schemas_project_agnostic_and_have_placeholders():
    project_name = os.environ.get("PROJECT_NAME", "").strip().lower() or "example-project"
    extra_terms = [
        t.strip().lower()
        for t in os.environ.get("PROJECT_TERMS", "").split(",")
        if t.strip()
    ]
    bad_terms = re.compile(
        "|".join(re.escape(t) for t in [project_name, *extra_terms, "odoo", "app"]),
        re.IGNORECASE,
    )
    placeholder_seen = False
    for path in sorted(CORE.glob("*.schema.json")):
        txt = path.read_text(encoding="utf-8")
        assert not bad_terms.search(txt), f"Project-specific term in {path}"
        if "{PROJECT_NAME}" in txt:
            placeholder_seen = True
    assert placeholder_seen, "Expected at least one {PROJECT_NAME} placeholder in core schemas"


def test_project_schemas_extend_core_when_present():
    """project overlays must extend core via $ref or allOf.

    If the project schemas directory doesn't exist, this test fails in RED
    and will pass once overlays are added in GREEN.
    """
    assert PROJECT.exists(), "Project schemas dir missing: .agents/schemas"
    overlays = list(PROJECT.glob("*.schema.json"))
    assert overlays, "Expected project overlays in .agents/schemas"
    for path in overlays:
        data = _read_json(path)
        assert "$schema" in data, f"$schema missing in {path}"
        txt = json.dumps(data)
        assert ".edison/core/schemas/" in txt or "$ref" in txt or "allOf" in data, (
            f"Overlay {path} must reference core schemas"
        )


def test_core_schemas_disallow_additional_properties_true():
    """Core schemas must be strict: additionalProperties must never be true."""
    violations: list[str] = []

    def walk(obj: object, ctx: str) -> None:
        if isinstance(obj, dict):
            if obj.get("additionalProperties") is True:
                violations.append(ctx)
            for k, v in obj.items():
                walk(v, f"{ctx}/{k}" if ctx else k)
        elif isinstance(obj, list):
            for idx, v in enumerate(obj):
                walk(v, f"{ctx}[{idx}]")

    for path in sorted(CORE.glob("*.schema.json")):
        walk(_read_json(path), path.name)

    assert not violations, (
        "additionalProperties: true must be removed from core schemas; "
        f"found at {violations}"
    )
