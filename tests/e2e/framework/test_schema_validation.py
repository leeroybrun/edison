from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import validate, ValidationError


CORE = Path(".edison/core/schemas")
PROJECT = Path(".agents/schemas")
STATE_MACHINE = Path(".edison/core/config/state-machine.yaml")


def _schema(name: str) -> dict:
    p = CORE / name
    return json.loads(p.read_text(encoding="utf-8"))


def test_session_json_validates():
    schema = _schema("session.schema.json")
    example = {
        "id": "session-123",
        "state": "Active",
        "createdAt": "2025-11-17T12:00:00Z",
        "lastActiveAt": "2025-11-17T12:30:00Z",
        "worktree": {
            "baseDirectory": "../{PROJECT_NAME}-worktrees",
            "path": ".project/sessions/active/session-123"
        },
        "timeoutMinutes": 60,
        "tasks": ["task-1", "task-2"],
        "qa": {"status": "pending"}
    }
    validate(instance=example, schema=schema)


def test_task_json_validates():
    schema = _schema("task.schema.json")
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
    schema = _schema("config.schema.json")
    config_yaml = """
project:
  name: my-project
session:
  worktree:
    baseDirectory: ../{PROJECT_NAME}-worktrees
  timeoutMinutes: 45
delegation:
  roles:
    - name: reviewer
      capabilities: ["qa", "review"]
validators:
  enabled: ["security", "performance"]
"""
    config = yaml.safe_load(config_yaml)
    validate(instance=config, schema=schema)


def test_task_status_enum_matches_state_machine():
    """Task.status enum must align with the canonical task state machine."""
    schema = _schema("task.schema.json")
    status_enum = schema["properties"]["status"]["enum"]
    assert status_enum, "task.schema.json must declare a non-empty status enum"

    assert STATE_MACHINE.exists(), "Missing state-machine.yaml in core config"
    sm = yaml.safe_load(STATE_MACHINE.read_text(encoding="utf-8")) or {}
    task_states_cfg = (
        (sm.get("statemachine") or {}).get("task") or {}
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


def test_pack_scenario_edison_full_yaml_validates_against_config_schema():
    """
    Pack scenario configs under fixtures/pack-scenarios must conform to the
    canonical config schema used for edison.yaml.
    """
    schema = _schema("config.schema.json")
    scenario_path = Path(
        ".edison/core/tests/fixtures/pack-scenarios/edison.full.yaml"
    )
    assert scenario_path.exists(), "Missing edison.full.yaml pack scenario fixture"
    config = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))

    # RED expectation: legacy schema/object shape mismatch causes validation to fail.
    validate(instance=config, schema=schema)


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
