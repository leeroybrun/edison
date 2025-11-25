from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout

REPO_ROOT = Path(__file__).resolve().parents[5]


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
@pytest.mark.skip(reason="Test references deprecated .agents/ structure - session templates moved to .edison/")
def test_template_has_state_and_validates_against_schema():
    tmpl = _load_json(REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json")
    schema = _load_json(REPO_ROOT / ".agents" / "sessions" / "session.schema.json")
    # RED: ensure required 'state' present and set to 'active' for new sessions
    assert "state" in tmpl, "TEMPLATE.json missing top-level 'state'"
    assert tmpl["state"] == "active", "TEMPLATE.json should default state to 'active'"
    errs = _minimal_jsonschema_validate(tmpl, schema)
    assert not errs, f"Template does not satisfy schema: {errs}"


@pytest.mark.fast
@pytest.mark.skip(reason="Test references deprecated .agents/ structure - session workflow moved to .edison/")
def test_docs_align_with_state_machine_terms():
    # The docs must mention the canonical session states and directory mapping
    workflow = _load_json(REPO_ROOT / ".agents" / "session-workflow.json")
    states = workflow.get("session", {}).get("states", [])
    assert set(states) == {"active", "closing", "validated"}
    text = (REPO_ROOT / ".agents" / "guidelines" / "SESSION_WORKFLOW.md").read_text()
    # Expect explicit mapping lines present in the guide
    assert "`.project/sessions/wip/` (active)" in text
    assert "`.project/sessions/done/` (closing)" in text
    assert "`.project/sessions/validated/` (validated)" in text


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.skip(reason="Test references deprecated .agents/ structure - needs update for .edison/")
def test_status_read_only_and_sync_git(tmp_path: Path):
    """Status must not create worktrees; sync-git performs creation.

    Steps:
      1) Create isolated repo + project structure with worktrees.enabled=false
      2) session new (no worktree created)
      3) session status --json (must NOT create worktree)
      4) session sync-git (creates worktree + updates session JSON)
    """
    repo_root = tmp_path
    # Initialize a real git repo
    def _git(*args: str) -> subprocess.CompletedProcess:
        return run_with_timeout(["git", *args], cwd=repo_root, capture_output=True, text=True)

    # Minimal .project layout
    for p in [
        ".project/tasks/todo", ".project/tasks/wip", ".project/tasks/done", ".project/tasks/validated", ".project/tasks/blocked",
        ".project/qa/waiting", ".project/qa/todo", ".project/qa/wip", ".project/qa/done", ".project/qa/validated",
        ".project/sessions/wip", ".project/sessions/done", ".project/sessions/validated",
        ".agents/sessions", ".agents/validators", ".agents/scripts/lib", ".agents/scripts/tests/e2e/helpers",
    ]:
        (repo_root / p).mkdir(parents=True, exist_ok=True)

    # Copy required scripts + libs from real repo
    real = REPO_ROOT
    for rel in [
        ".agents/scripts/session",
        ".agents/scripts/lib/task.py",
        ".agents/scripts/lib/sessionlib.py",
        ".agents/sessions/TEMPLATE.json",
        ".agents/sessions/session.schema.json",
        ".agents/session-workflow.json",
    ]:
        src = real / rel
        dest = repo_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())

    # Manifest override: disable auto worktrees so session new doesn't create one
    manifest = json.loads((real / ".agents" / "manifest.json").read_text())
    manifest.setdefault("worktrees", {})
    manifest["worktrees"].update({"enabled": False})
    (repo_root / ".agents" / "manifest.json").write_text(json.dumps(manifest, indent=2))

    env = os.environ.copy()
    env.update({"project_ROOT": str(repo_root)})

    def _run(args: list[str]) -> subprocess.CompletedProcess:
        # Always invoke via python3 to avoid exec permission issues in temp repos
        return run_with_timeout(["python3", *args], cwd=repo_root, env=env, capture_output=True, text=True)

    sid = "test-sync-git"
    # 2) Create session in a non-git directory (so no worktree is auto-created)
    r = _run([str(repo_root / ".agents" / "scripts" / "session"), "new", "--owner", "tester", "--session-id", sid, "--mode", "start"])
    assert r.returncode == 0, r.stderr
    sess_path = repo_root / ".project" / "sessions" / "wip" / f"{sid}.json"
    data = json.loads(sess_path.read_text())
    wt_hint_str = data.get("git", {}).get("worktreePath") or str(repo_root / ".worktrees" / sid)
    wt_hint = Path(wt_hint_str)
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
