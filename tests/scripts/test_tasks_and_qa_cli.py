import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def run(script: str, args: list[str], env: dict) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPTS_DIR / script), *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=env["AGENTS_PROJECT_ROOT"],
        check=True,
    )


def make_project_root(tmp_path: Path) -> Path:
    (tmp_path / ".project" / "tasks" / "todo").mkdir(parents=True)
    (tmp_path / ".project" / "qa" / "waiting").mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def write_task_template(root: Path) -> None:
    template = root / ".project" / "tasks" / "TEMPLATE.md"
    template.write_text(
        "\n".join(
            [
                "# PPP-waveN-slug",
                "**Task ID:** PPP-waveN-slug",
                "**Priority Slot:** PPP",
                "**Wave:** waveN",
                "**Task Type:** (ui-component | api-route | database-schema | test-suite | refactoring | full-stack-feature | ...)",
                "**Owner:** _unassigned_",
                "**Status:** todo | wip | done | validated",
                "**Created:** YYYY-MM-DD",
                "**Parent Task:** _none_",
                "**Continuation ID:** _none_",
            ]
        ),
        encoding="utf-8",
    )


def test_allocate_id_uses_json_output(tmp_path: Path):
    root = make_project_root(tmp_path)
    # seed an existing child id so next = base.2
    existing = root / ".project" / "tasks" / "todo" / "201.1-demo.md"
    existing.write_text("placeholder")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    proc = run("tasks/allocate-id", ["--base", "201", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["nextId"] == "201.2"


def test_mark_delegated_updates_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_file = root / ".project" / "tasks" / "todo" / "111-wave1-demo.md"
    task_file.write_text(
        "\n".join(
            [
                "# Task",
                "- **Session Info:**",
                "  - **Primary Model:** gpt-4",
                "  - **Last Active:** 2000-01-01T00:00:00Z",
            ]
        )
    )
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    proc = run("tasks/mark-delegated", ["111-wave1-demo" , "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["delegated"] is True
    updated = task_file.read_text()
    assert "Delegated" in updated


def test_cleanup_stale_locks_json(tmp_path: Path, monkeypatch):
    root = make_project_root(tmp_path)
    locks_dir = root / ".project" / "tasks" / "_locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock = locks_dir / "stale.lock"
    lock.write_text("pid=999999")
    old = 0
    os.utime(lock, (old, old))
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    proc = run("tasks/cleanup-stale-locks", ["--max-age", "0", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["removed"] == 1
    assert not lock.exists()


def test_qa_new_creates_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    template = root / ".project" / "qa" / "TEMPLATE.md"
    template.write_text("""# PPP-waveN-slug-qa\n**Priority Slot:** PPP\n**Validator Owner:** _unassigned_\n**Status:** waiting | todo | wip | done | validated\n**Created:** YYYY-MM-DD\n**Evidence Directory:** `.project/qa/validation-evidence/task-XXXX/`\n**Continuation ID:** _none_\n""")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa/new", ["150-wave1-demo", "--owner", "alice", "--json"], env)
    payload = json.loads(result.stdout.strip())
    qa_path = root / payload["qaPath"]
    assert qa_path.exists()


def test_qa_round_appends(tmp_path: Path):
    root = make_project_root(tmp_path)
    qa_file = root / ".project" / "qa" / "waiting" / "150-wave1-demo-qa.md"
    qa_file.write_text("# 150-wave1-demo-qa\n")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa/round", ["--task", "150-wave1-demo", "--status", "approved", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["taskId"] == "150-wave1-demo"
    content = qa_file.read_text()
    assert "Round 1" in content


def test_tasks_link_updates_session_graph(tmp_path: Path):
    root = make_project_root(tmp_path)
    parent = root / ".project" / "tasks" / "todo" / "200-wave1-demo.md"
    child = root / ".project" / "tasks" / "todo" / "200.1-wave1-child.md"
    parent.write_text("# Task parent\n")
    child.write_text("# Task child\n")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("tasks/link", ["200-wave1-demo", "200.1-wave1-child", "--session", "s123", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["sessionId"] == "s123"
    # ensure session graph persisted
    session_files = list((root / ".project" / "sessions").rglob("session.json"))
    assert session_files, "session.json not created"
    session_data = json.loads(session_files[0].read_text())
    tasks = session_data.get("tasks", {})
    assert "200-wave1-demo" in tasks
    assert "200.1-wave1-child" in tasks
    assert tasks["200.1-wave1-child"].get("parentId") == "200-wave1-demo"


def test_tasks_new_creates_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_task_template(root)
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    proc = run("tasks/new", ["--id", "150", "--wave", "wave1", "--slug", "demo", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    path = root / payload["path"]
    assert path.exists()
    content = path.read_text()
    assert "150-wave1-demo" in content


def test_tasks_status_moves_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_path = root / ".project" / "tasks" / "todo" / "150-wave1-demo.md"
    task_path.write_text("status: todo\n")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    run("tasks/status", ["150-wave1-demo", "--status", "wip", "--json"], env)
    moved = root / ".project" / "tasks" / "wip" / "150-wave1-demo.md"
    assert moved.exists()


def test_tasks_ready_moves_wip_to_done(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_id = "150-wave1-demo"

    # session scoped wip task + qa waiting
    wip_task = root / ".project" / "sessions" / "wip" / "s1" / "tasks" / "wip"
    wip_task.mkdir(parents=True, exist_ok=True)
    wip_path = wip_task / f"task-{task_id}.md"
    wip_path.write_text("status: wip\n")

    qa_waiting = root / ".project" / "sessions" / "waiting" / "s1" / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    qa_wait_path = qa_waiting / f"{task_id}-qa.md"
    qa_wait_path.write_text("# qa waiting\n")

    # evidence files
    evidence = root / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
    evidence.mkdir(parents=True, exist_ok=True)
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        (evidence / name).write_text("ok\n")
    (evidence / "implementation-report.json").write_text("{}")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    run("tasks/ready", [task_id, "--session", "s1", "--json"], env)

    done_path = root / ".project" / "sessions" / "done" / "s1" / "tasks" / "done" / f"task-{task_id}.md"
    qa_todo = root / ".project" / "sessions" / "todo" / "s1" / "qa" / "todo" / f"{task_id}-qa.md"
    assert done_path.exists()
    assert qa_todo.exists()


def test_qa_bundle_outputs_manifest(tmp_path: Path):
    root = make_project_root(tmp_path)
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    # register tasks in session graph
    from edison.core.session import graph as session_graph
    os.environ["AGENTS_PROJECT_ROOT"] = str(root)
    session_graph.register_task("s1", "150-wave1-demo", owner="alice", status="done")
    session_graph.link_tasks("s1", "150-wave1-demo", "150.1-wave1-child")

    result = run("qa/bundle", ["150-wave1-demo", "--session", "s1", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["sessionId"] == "s1"
    assert payload["rootTask"] == "150-wave1-demo"
    assert isinstance(payload["tasks"], list)


def test_qa_promote_moves_state(tmp_path: Path):
    root = make_project_root(tmp_path)
    qa_waiting = root / ".project" / "qa" / "waiting" / "150-wave1-demo-qa.md"
    qa_waiting.write_text("status: waiting\n")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    run("qa/promote", ["--task", "150-wave1-demo", "--to", "todo", "--json"], env)
    qa_todo = root / ".project" / "qa" / "todo" / "150-wave1-demo-qa.md"
    assert qa_todo.exists()


def test_guidelines_audit_writes_evidence(tmp_path: Path):
    root = make_project_root(tmp_path)
    # create a simple guideline file
    gdir = root / ".edison" / "core" / "guidelines"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "core.md").write_text("Core guideline text")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa/guidelines_audit.py", ["--json"], env)
    summary = json.loads(result.stdout.strip())
    evidence_root = root / ".project" / "qa" / "validation-evidence" / "fix-9-guidelines-audit"
    assert summary["duplicationPairs"] >= 0
    assert (evidence_root / "summary.json").exists()
