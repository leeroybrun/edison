from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout

from tests.helpers.paths import get_repo_root

REPO_ROOT = get_repo_root()


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text())


def _minimal_jsonschema_validate(instance: dict, schema: dict) -> list[str]:
    """Very small validator for the subset used in session.schema.json.

    Supports: type=object/string/integer/array, required, properties, enum, items.
    Returns a list of validation error strings (empty means valid).
    """
    errors: list[str] = []

    def check(node: object, sch: dict, path: str) -> None:
        t = sch.get("type")
        if t == "object":
            if not isinstance(node, dict):
                errors.append(f"{path}: expected object, got {type(node).__name__}")
                return
            req = sch.get("required", [])
            for k in req:
                if k not in node:
                    errors.append(f"{path}: missing required property '{k}'")
            props = sch.get("properties", {})
            for k, sub in props.items():
                if k in node:
                    check(node[k], sub, f"{path}.{k}")
        elif t == "array":
            if not isinstance(node, list):
                errors.append(f"{path}: expected array, got {type(node).__name__}")
                return
            item_s = sch.get("items")
            if isinstance(item_s, dict):
                for i, it in enumerate(node):
                    check(it, item_s, f"{path}[{i}]")
        elif t == "string":
            if not isinstance(node, str):
                errors.append(f"{path}: expected string, got {type(node).__name__}")
                return
            if "enum" in sch and node not in sch["enum"]:
                errors.append(f"{path}: '{node}' not in enum {sch['enum']}")
        elif t == "integer":
            if not isinstance(node, int):
                errors.append(f"{path}: expected integer, got {type(node).__name__}")
        # Ignore additionalProperties/defaults for this minimal check

    check(instance, schema, "$")
    return errors


@pytest.mark.fast
@pytest.mark.skip(reason="Test references deprecated .agents/ structure - session templates moved to bundled edison.data")
def test_template_has_state_and_validates_against_schema():
    # NOTE: Session templates are now in bundled edison.data/templates/session.template.json
    # Schema validation should be done via the bundled template
    from edison.data import get_data_path
    tmpl = _load_json(get_data_path("templates", "session.template.json"))
    schema = _load_json(get_data_path("schemas", "session.schema.json"))
    # RED: ensure required 'state' present and set to 'active' for new sessions
    assert "state" in tmpl, "TEMPLATE.json missing top-level 'state'"
    assert tmpl["state"] == "active", "TEMPLATE.json should default state to 'active'"
    errs = _minimal_jsonschema_validate(tmpl, schema)
    assert not errs, f"Template does not satisfy schema: {errs}"


@pytest.mark.fast
@pytest.mark.skip(reason="Test references deprecated structure - session workflow is now in bundled state-machine.yaml")
def test_docs_align_with_state_machine_terms():
    """Verify session state machine defines expected states.
    
    NOTE: The canonical session workflow definition is now in:
    - bundled: edison.data/config/state-machine.yaml
    - project override: .edison/config/state-machine.yaml
    
    Accessed via WorkflowConfig domain config.
    """
    from edison.core.config.domains.workflow import WorkflowConfig
    
    workflow_config = WorkflowConfig()
    session_states = workflow_config.get_states("session")
    
    # Verify expected session states are defined
    expected_states = {"active", "closing", "validated"}
    assert set(session_states) == expected_states, (
        f"Expected session states {expected_states}, got {set(session_states)}"
    )


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.skip(reason="Pending rewrite for edison CLI session sync-git coverage")
def test_status_read_only_and_sync_git(tmp_path: Path):
    """Placeholder for edison session sync-git behavior (legacy .agents flow removed)."""
    pytest.skip("Rewrite with edison session CLI once sync-git behavior is defined")
    # Initialize git repo AFTER session creation so status runs inside a repo
    cp = _git("init", "-b", "main")
    assert cp.returncode == 0, cp.stderr
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test User")
    (repo_root / "README.md").write_text("# Tmp Repo\n")
    _git("add", "-A")
    assert _git("commit", "-m", "init").returncode == 0

    # 3) status must not create a worktree automatically
    assert not wt_hint.exists(), "worktree should not exist before sync-git"
    s = _run([str(repo_root / ".agents" / "scripts" / "session"), "status", sid, "--json"])
    assert s.returncode == 0, s.stderr
    assert not wt_hint.exists(), "status must be read-only and not create worktrees"
    # 4) sync-git should create and update JSON
    sg = _run([str(repo_root / ".agents" / "scripts" / "session"), "sync-git", sid])
    assert sg.returncode == 0, sg.stderr
    assert wt_hint.exists(), "sync-git should create the worktree"
    data2 = json.loads(sess_path.read_text())
    assert data2.get("git", {}).get("worktreePath"), "session JSON should carry git metadata after sync"
