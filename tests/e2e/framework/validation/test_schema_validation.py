from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import validate, ValidationError
from edison.data import get_data_path


CORE = get_data_path("schemas")
PROJECT = Path(".edison/schemas")
# Canonical statemachine lives in workflow.yaml (workflow.statemachine.*)
WORKFLOW = get_data_path("config", "workflow.yaml")


def _load_schema(name: str) -> dict:
    p = CORE / name
    return json.loads(p.read_text(encoding="utf-8"))


def test_session_json_validates():
    schema = _load_schema("domain/session.schema.json")
    example = {
        "id": "session-123",
        "state": "active",
        "phase": "implementation",
        "meta": {
            "sessionId": "session-123",
            "owner": "owner-123",
            "createdAt": "2025-11-17T12:00:00Z",
            "lastActive": "2025-11-17T12:30:00Z",
            "status": "active",
        },
        "ready": True,
        "git": {"baseBranch": "main", "branchName": None, "worktreePath": None},
    }
    validate(instance=example, schema=schema)


def test_task_json_validates():
    schema = _load_schema("domain/task.schema.json")
    example = {
        "id": "task-42",
        "title": "Implement generic schema framework",
        "type": "feature",
        "status": "todo",
        "priority": "medium",
        "tddEvidence": {
            "red": ".project/qa/validation-evidence/w2-g4/RED-output.txt",
            "green": ".project/qa/validation-evidence/w2-g4/GREEN-output.txt",
            "refactor": ".project/qa/validation-evidence/w2-g4/REFACTOR-output.txt"
        },
        "acceptanceCriteria": [
            "Core schemas are generic",
            "Overlays extend core",
            "Tests pass"
        ],
        "dependsOn": []
    }
    validate(instance=example, schema=schema)


def test_config_yaml_validates():
    schema = _load_schema("config/config.schema.json")
    config_yaml = """
project:
  name: my-project
session:
  timeoutMinutes: 45
  worktree:
    uuidSuffixLength: 6
delegation:
  implementers:
    primary: codex
    fallbackChain: [claude]
validators:
  enabled: ["security", "performance"]
"""
    config = yaml.safe_load(config_yaml)
    validate(instance=config, schema=schema)


def test_task_status_enum_matches_state_machine():
    """Task.status enum must align with the canonical task state machine."""
    schema = _load_schema("domain/task.schema.json")
    status_enum = schema["properties"]["status"]["enum"]
    assert status_enum, "domain/task.schema.json must declare a non-empty status enum"

    assert WORKFLOW.exists(), "Missing workflow.yaml in core config"
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")) or {}
    task_states_cfg = (
        ((wf.get("workflow") or {}).get("statemachine") or {}).get("task") or {}
    ).get("states") or {}
    if isinstance(task_states_cfg, dict):
        task_states = list(task_states_cfg.keys())
    else:
        task_states = task_states_cfg
    assert task_states, "state-machine.yaml must declare task states"

    # RED expectation: currently mismatched (e.g., 'doing' vs 'wip', 'review' vs 'validated').
    assert set(status_enum) == set(task_states), (
        f"Task status enum {status_enum} must match task state-machine states {task_states}"
    )


@pytest.mark.skip(reason="Fixture file moved/missing - needs update for new layout")
def test_pack_scenario_edison_full_yaml_validates_against_config_load_schema():
    """
    Pack scenario configs under fixtures/pack-scenarios must conform to the
    canonical config schema used for edison.yaml.
    """
    schema = _load_schema("config/config.schema.json")
    scenario_path = Path(
        ".edison/core/tests/fixtures/pack-scenarios/edison.full.yaml"
    )
    assert scenario_path.exists(), "Missing edison.full.yaml pack scenario fixture"
    config = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))

    # RED expectation: legacy schema/object shape mismatch causes validation to fail.
    validate(instance=config, schema=schema)


@pytest.mark.skip(reason="Project schema overlays not applicable to framework tests")
def test_project_specific_fields_validate_against_project_overlays():
    """Overlay should allow project-specific metadata on tasks while core remains generic."""
    # Load core and overlay via simple composition: overlay uses allOf/$ref
    # Here we check overlay schema exists and allows project-specific fields.
    overlays = list(PROJECT.glob("*.schema.json"))
    assert overlays, "project overlays missing; expected at least one project schema."

    overlay_task = None
    for p in overlays:
        if "task" in p.name:
            overlay_task = json.loads(p.read_text(encoding="utf-8"))
            break
    assert overlay_task is not None, "Task overlay schema not found in .agents/schemas"

    example = {
        "id": "task-100",
        "title": "project extension example",
        "type": "feature",
        "status": "doing",
        "priority": "high",
        "projectTaskType": "api",
        "projectMetadata": {
            "affectsApp": True,
            "requiresOdooSync": False
        }
    }

    # Basic structural validation: if overlay uses allOf with $ref to core, jsonschema.validate will work
    # RED: fails because overlays/schemas missing. GREEN: passes once overlays exist.
    validate(instance=example, schema=overlay_task)
