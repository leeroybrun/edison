from __future__ import annotations

import json
from pathlib import Path


def test_isolated_project_env_has_complete_scaffolding(isolated_project_env: Path) -> None:
    """isolated_project_env should provide minimal Edison scaffolding.

    Verifies:
    - Core .project templates exist (tasks + QA)
    - Core .edison session template and workflow spec exist
    - TDD wrapper for tasks/ready is present under .edison/scripts
    """
    root = isolated_project_env

    # .project templates
    task_tpl = root / ".project" / "tasks" / "TEMPLATE.md"
    qa_tpl = root / ".project" / "qa" / "TEMPLATE.md"
    assert task_tpl.is_file(), f"Missing task template: {task_tpl}"
    assert qa_tpl.is_file(), f"Missing QA template: {qa_tpl}"

    task_text = task_tpl.read_text(encoding="utf-8")
    assert "Task ID" in task_text or "Task:" in task_text, "Task template should describe task metadata"
    assert "Status:" in task_text, "Task template should include status field"

    qa_text = qa_tpl.read_text(encoding="utf-8")
    assert "Validator Owner" in qa_text, "QA template should describe validator owner"
    assert "Status:" in qa_text, "QA template should include status field"

    # Session template + workflow
    session_tpl = root / ".edison" / "sessions" / "TEMPLATE.json"
    assert session_tpl.is_file(), f"Missing session template: {session_tpl}"
    session_data = json.loads(session_tpl.read_text(encoding="utf-8"))
    assert isinstance(session_data, dict), "Session template must be a JSON object"
    assert session_data.get("state") == "active", "Session template should default state to 'active'"
    meta = session_data.get("meta") or {}
    for key in ("sessionId", "owner", "mode", "status", "createdAt", "lastActive"):
        assert key in meta, f"Session template meta missing required key: {key}"

    workflow_path = root / ".edison" / "session-workflow.json"
    assert workflow_path.is_file(), f"Missing session workflow spec: {workflow_path}"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    session_cfg = (workflow.get("session") or {})
    states = set(session_cfg.get("states") or [])
    assert {"active", "closing", "validated"} <= states, "Session workflow must include canonical states"

    # TDD wrapper for tasks/ready in project sandbox
    ready_wrapper = root / ".edison" / "scripts" / "tasks" / "ready"
    assert ready_wrapper.is_file(), f"Missing tasks/ready wrapper in isolated project env: {ready_wrapper}"
