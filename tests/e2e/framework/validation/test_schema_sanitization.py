from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from edison.data import get_data_path
from edison.core.utils.io import read_yaml


# Use the source schemas directory for testing in the Edison repo
CORE = get_data_path("schemas")
PROJECT = Path(".agents/schemas")


def _read_schema(p: Path) -> dict:
    data = read_yaml(p, default={}, raise_on_error=True)
    assert isinstance(data, dict)
    return data


def test_core_schemas_exist():
    # Schemas organized into subfolders by category
    expected = {
        "domain/session.schema.yaml",
        "domain/task.schema.yaml",
        "domain/qa.schema.yaml",
        "config/config.schema.yaml",
        "config/delegation.schema.yaml",
        "manifests/manifest.schema.yaml",
    }
    assert CORE.exists(), f"Core schemas directory missing: {CORE}"
    present = {str(p.relative_to(CORE)) for p in CORE.rglob("*.schema.yaml")}
    missing = sorted(expected - present)
    assert not missing, f"Missing core schemas: {missing}"


def test_no_legacy_edison_config_schemas():
    """
    There must be a single canonical config schema (config.schema.yaml).

    Legacy Draft-07 config schemas (edison.schema.*, edison-config.schema.*)
    should be removed or folded into the canonical Draft-2020-12 schema.
    """
    legacy = sorted(
        p.name
        for p in CORE.rglob("edison*.schema.*")
        if p.name not in {"edison-task.schema.yaml"}  # future-proof if added
    )
    assert not legacy, (
        "Legacy Edison config schemas should be removed or aliased via config.schema.yaml; "
        f"found: {legacy}"
    )


def test_core_schemas_valid_and_have_schema_decl():
    for path in sorted(CORE.rglob("*.schema.yaml")):
        data = _read_schema(path)
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
    # Use word boundaries to avoid matching substrings like "app" in "applied"
    bad_terms = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in [project_name, *extra_terms, "odoo"]) + r")\b",
        re.IGNORECASE,
    )
    placeholder_seen = False
    for path in sorted(CORE.rglob("*.schema.yaml")):
        txt = path.read_text(encoding="utf-8")
        match = bad_terms.search(txt)
        assert not match, f"Project-specific term '{match.group()}' in {path}"
        if "{PROJECT_NAME}" in txt:
            placeholder_seen = True
    assert placeholder_seen, "Expected at least one {PROJECT_NAME} placeholder in core schemas"


@pytest.mark.skip(reason="Project overlays test applies to target projects, not Edison repo")
def test_project_schemas_extend_core_when_present():
    """project overlays must extend core via $ref or allOf.

    If the project schemas directory doesn't exist, this test fails in RED
    and will pass once overlays are added in GREEN.
    """
    assert PROJECT.exists(), "Project schemas dir missing: .agents/schemas"
    overlays = list(PROJECT.glob("*.schema.yaml"))
    assert overlays, "Expected project overlays in .agents/schemas"
    for path in overlays:
        data = _read_schema(path)
        assert "$schema" in data, f"$schema missing in {path}"
        txt = str(data)
        assert ".edison/core/schemas/" in txt or "$ref" in txt or "allOf" in data, (
            f"Overlay {path} must reference core schemas"
        )


def test_core_schemas_disallow_additional_properties_true():
    """Core schemas must be strict: additionalProperties must never be true.
    
    Some exceptions are allowed for schemas that need extensibility:
    - orchestrators: profiles can have custom keys
    - statemachine: domain and state names are dynamic
    - meta: user-defined metadata
    """
    # Known exceptions where additionalProperties: true is intentional
    allowed_exceptions = {
        "config/config.schema.yaml",  # root level allows unknown sections (defaults.yaml has many internal sections)
        "config/config.schema.yaml/properties/orchestrators",  # dynamic profiles
        "config/config.schema.yaml/properties/session",  # session has many internal config properties
        "config/config.schema.yaml/properties/session/properties/worktree",  # worktree has internal properties
        "config/config.schema.yaml/properties/packs/oneOf[0]",  # packs object form has internal properties
        "config/config.schema.yaml/$defs/delegation",  # delegation has internal properties
        "config/state-machine-rich.schema.yaml/properties/statemachine/patternProperties/^[A-Za-z0-9_-]+$",  # domain names
        "config/state-machine-rich.schema.yaml/properties/statemachine/patternProperties/^[A-Za-z0-9_-]+$/properties/states/patternProperties/^[A-Za-z0-9_-]+$",  # state names
        "domain/session.schema.yaml/properties/meta",  # user metadata
    }
    violations: list[str] = []

    def walk(obj: object, ctx: str) -> None:
        if isinstance(obj, dict):
            if obj.get("additionalProperties") is True and ctx not in allowed_exceptions:
                violations.append(ctx)
            for k, v in obj.items():
                walk(v, f"{ctx}/{k}" if ctx else k)
        elif isinstance(obj, list):
            for idx, v in enumerate(obj):
                walk(v, f"{ctx}[{idx}]")

    for path in sorted(CORE.rglob("*.schema.yaml")):
        walk(_read_schema(path), str(path.relative_to(CORE)))

    assert not violations, (
        "additionalProperties: true must be removed from core schemas; "
        f"found at {violations}"
    )
