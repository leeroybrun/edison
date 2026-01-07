from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_all_and_reload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_session(project_root: Path, session_id: str, *, state: str = "active", meta: dict | None = None) -> None:
    sessions_dir = project_root / ".project" / "sessions" / "wip" / session_id
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / "session.json"
    now = _now_iso()
    session_data = {
        "id": session_id,
        "meta": {
            "sessionId": session_id,
            "owner": "test-owner",
            "mode": "start",
            "status": state,
            "createdAt": now,
            "lastActive": now,
            **(meta or {}),
        },
        "state": state,
        "tasks": {},
        "qa": {},
        "git": {"worktreePath": None, "branchName": None, "baseBranch": None},
        "activityLog": [{"timestamp": now, "message": "Session created"}],
    }
    session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")


def _write_task(
    project_root: Path,
    *,
    task_id: str,
    state_dir: str,
    session_id: str,
    parent_id: str | None = None,
) -> None:
    task_dir = project_root / ".project" / "tasks" / state_dir
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.md"
    fm_lines = [
        "---",
        f"id: {task_id}",
        'title: "Demo"',
        f"session_id: {session_id}",
    ]
    if parent_id:
        fm_lines.extend(
            [
                "relationships:",
                "  - type: parent",
                f"    target: {parent_id}",
            ]
        )
    fm_lines.append("---")
    task_file.write_text("\n".join(fm_lines) + "\n\n# Demo\n", encoding="utf-8")


@pytest.fixture
def repo_env(isolated_project_env: Path) -> Path:
    # Minimal required project structure for TaskRepository + session store.
    (isolated_project_env / ".project" / "tasks").mkdir(parents=True, exist_ok=True)
    (isolated_project_env / ".project" / "tasks" / "TEMPLATE.md").write_text("# TEMPLATE\n", encoding="utf-8")
    (isolated_project_env / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    (isolated_project_env / ".project" / "qa" / "validation-reports").mkdir(parents=True, exist_ok=True)
    reset_all_and_reload()
    return isolated_project_env


def test_completion_complete_when_roots_validated_and_children_done(repo_env: Path) -> None:
    from edison.core.session.next import compute_next

    sid = "s1"
    _write_session(repo_env, sid, state="active")

    _write_task(repo_env, task_id="t1", state_dir="validated", session_id=sid)
    _write_task(repo_env, task_id="t1.1", state_dir="done", session_id=sid, parent_id="t1")

    payload = compute_next(sid, scope=None, limit=0)

    completion = payload.get("completion") or {}
    assert completion.get("isComplete") is True
    assert completion.get("reasonsIncomplete") == []

    continuation = payload.get("continuation") or {}
    assert continuation.get("shouldContinue") is False


def test_completion_incomplete_when_root_not_validated(repo_env: Path) -> None:
    from edison.core.session.next import compute_next

    sid = "s2"
    _write_session(repo_env, sid, state="active")

    _write_task(repo_env, task_id="t1", state_dir="done", session_id=sid)
    _write_task(repo_env, task_id="t1.1", state_dir="done", session_id=sid, parent_id="t1")

    payload = compute_next(sid, scope=None, limit=0)

    completion = payload.get("completion") or {}
    assert completion.get("isComplete") is False
    reasons = completion.get("reasonsIncomplete") or []
    assert reasons, "Expected at least one reason when session is incomplete"

    continuation = payload.get("continuation") or {}
    assert continuation.get("shouldContinue") is True
    assert "{sessionId}" not in str(continuation.get("prompt") or ""), "Prompt should be formatted, not templated"


def test_completion_policy_all_tasks_validated_is_strict(repo_env: Path) -> None:
    from edison.core.session.next import compute_next

    # Override continuation policy for this project root.
    write_yaml(
        repo_env / ".edison" / "config" / "continuation.yaml",
        {"continuation": {"completionPolicy": "all_tasks_validated"}},
    )
    reset_all_and_reload()

    sid = "s3"
    _write_session(repo_env, sid, state="active")

    _write_task(repo_env, task_id="t1", state_dir="validated", session_id=sid)
    _write_task(repo_env, task_id="t1.1", state_dir="done", session_id=sid, parent_id="t1")

    payload = compute_next(sid, scope=None, limit=0)
    completion = payload.get("completion") or {}
    assert completion.get("policy") == "all_tasks_validated"
    assert completion.get("isComplete") is False


def test_completion_only_flag_outputs_minimal_payload(repo_env: Path, monkeypatch, capsys) -> None:
    import sys

    from edison.core.session import next as session_next

    sid = "s4"
    _write_session(repo_env, sid, state="active")
    _write_task(repo_env, task_id="t1", state_dir="done", session_id=sid)

    monkeypatch.setattr(
        sys,
        "argv",
        ["session-next", sid, "--json", "--completion-only"],
    )
    session_next.main()

    out = capsys.readouterr().out
    data = json.loads(out)
    assert set(data.keys()) == {"sessionId", "completion", "continuation"}
