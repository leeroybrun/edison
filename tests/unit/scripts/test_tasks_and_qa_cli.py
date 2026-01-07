import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root

EDISON_ROOT = get_repo_root()


def run(domain: str, command: str, args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Execute a CLI command using python -m edison.cli.<domain>.<command>."""
    cmd = [sys.executable, "-m", f"edison.cli.{domain}.{command}", *args]
    # Ensure subprocess imports the local source tree (not an unrelated installed package).
    # This keeps CLI subprocess tests deterministic across Python installations.
    src_root = str(EDISON_ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_root if not existing else f"{src_root}{os.pathsep}{existing}"
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=EDISON_ROOT,
        check=True,
    )


def make_project_root(tmp_path: Path) -> Path:
    (tmp_path / ".project" / "tasks" / "todo").mkdir(parents=True)
    (tmp_path / ".project" / "qa" / "waiting").mkdir(parents=True)
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)
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
    proc = run("task", "allocate_id", ["--parent", "201", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["nextId"] == "201.2"


def test_mark_delegated_updates_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_file = root / ".project" / "tasks" / "todo" / "111-wave1-demo.md"
    task_file.write_text(
        """---
id: "111-wave1-demo"
title: "Demo Task"
state: "todo"
---

# Demo Task

Demo description
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    proc = run("task", "mark_delegated", ["111-wave1-demo" , "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["delegated"] is True
    updated = task_file.read_text()
    assert "delegated_to" in updated


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
    proc = run("task", "cleanup_stale_locks", ["--max-age", "0", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["removed"] == 1
    assert not lock.exists()


def test_qa_new_creates_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    template = root / ".project" / "qa" / "TEMPLATE.md"
    template.write_text("""# PPP-waveN-slug-qa\n**Priority Slot:** PPP\n**Validator Owner:** _unassigned_\n**Status:** waiting | todo | wip | done | validated\n**Created:** YYYY-MM-DD\n**Evidence Directory:** `.project/qa/validation-reports/task-XXXX/`\n**Continuation ID:** _none_\n""")
    # qa new requires the task to exist.
    (root / ".project" / "tasks" / "todo" / "150-wave1-demo.md").write_text(
        """---
id: "150-wave1-demo"
title: "Demo Task"
---

# Demo Task
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa", "new", ["150-wave1-demo", "--owner", "alice", "--json"], env)
    payload = json.loads(result.stdout.strip())
    qa_path = root / payload["qaPath"]
    assert qa_path.exists()


def test_qa_round_appends(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_id = "150-wave1-demo"
    qa_file = root / ".project" / "qa" / "waiting" / f"{task_id}-qa.md"
    qa_file.write_text(f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA for {task_id}"
state: "waiting"
round: 1
---

# QA for {task_id}

Validation scope
""")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa.round", "set_status", [task_id, "--status", "approve", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["taskId"] == task_id
    assert payload["round"] == 2
    content = qa_file.read_text()
    assert "round_history" in content
    assert "approve" in content


def test_qa_round_set_status_does_not_create_evidence_dir(tmp_path: Path) -> None:
    """`edison qa round set-status` appends QA history only.

    Evidence directories are created explicitly via `edison qa round prepare`.
    """
    root = make_project_root(tmp_path)
    task_id = "151-wave1-no-evidence"
    qa_file = root / ".project" / "qa" / "waiting" / f"{task_id}-qa.md"
    qa_file.write_text(
        f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA for {task_id}"
state: "waiting"
round: 1
---

# QA for {task_id}
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa.round", "set_status", [task_id, "--status", "approve", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["round"] == 2

    evidence_root = root / ".project" / "qa" / "validation-reports" / task_id
    assert not evidence_root.exists(), "qa round set-status should not create evidence dirs"


def test_qa_validate_reports_cli_disabled_by_config_instead_of_cli_missing(tmp_path: Path) -> None:
    root = make_project_root(tmp_path)
    task_id = "160-wave1-validate-delegation"

    # Force-disable CLI engines for this test to ensure deterministic behavior (no external CLIs).
    (root / ".edison" / "config" / "orchestration.yaml").write_text(
        "orchestration:\n  allowCliEngines: false\n",
        encoding="utf-8",
    )

    # Minimal task + QA so validation can build a roster and write evidence.
    (root / ".project" / "tasks" / "todo" / f"{task_id}.md").write_text(
        f"""---
id: "{task_id}"
title: "Demo task for validate delegation"
state: "todo"
---

# Demo
""",
        encoding="utf-8",
    )
    (root / ".project" / "qa" / "waiting" / f"{task_id}-qa.md").write_text(
        f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA for {task_id}"
state: "waiting"
round: 1
---

# QA for {task_id}
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    # Default config disables CLI engines; validate should delegate and explain why.
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        run("qa", "validate", [task_id, "--execute", "--blocking-only"], env)

    assert excinfo.value.returncode == 1
    out = excinfo.value.stdout
    assert "ORCHESTRATOR ACTION REQUIRED" in out
    assert "disabled by config" in out
    assert "allowCliEngines" in out


def test_qa_validate_enforces_session_worktree_for_execution(tmp_path: Path) -> None:
    root = make_project_root(tmp_path)
    task_id = "161-wave1-validate-worktree"
    session_id = "python-pid-12345"

    # Minimal task + QA so validation is runnable if it got past worktree enforcement.
    (root / ".project" / "tasks" / "todo" / f"{task_id}.md").write_text(
        f"""---
id: "{task_id}"
title: "Demo task for worktree enforcement"
state: "todo"
---

# Demo
""",
        encoding="utf-8",
    )
    (root / ".project" / "qa" / "waiting" / f"{task_id}-qa.md").write_text(
        f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA for {task_id}"
state: "waiting"
round: 1
---

# QA for {task_id}
""",
        encoding="utf-8",
    )

    worktree = root / "worktrees" / session_id
    worktree.mkdir(parents=True, exist_ok=True)

    # Create a session record that declares a worktree path.
    session_dir = root / ".project" / "sessions" / "wip" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "session.json").write_text(
        json.dumps(
            {
                "id": session_id,
                "state": "wip",
                "phase": "implementation",
                "meta": {"sessionId": session_id, "status": "wip", "owner": "alice"},
                "git": {"worktreePath": str(worktree)},
                "ready": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    env["AGENTS_SESSION"] = session_id

    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        run("qa", "validate", [task_id, "--execute"], env)

    assert excinfo.value.returncode == 2
    assert "WORKTREE ENFORCEMENT" in (excinfo.value.stderr or "")
    assert str(worktree) in (excinfo.value.stderr or "")

def test_task_new_parent_sets_frontmatter_and_updates_parent(tmp_path: Path) -> None:
    """`edison task new --parent` must persist parent/child links in frontmatter."""
    root = make_project_root(tmp_path)
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    # Create parent
    parent_id = "200-wave1-parent"
    parent_proc = run("task", "new", ["--id", "200", "--wave", "wave1", "--slug", "parent", "--json"], env)
    parent_payload = json.loads(parent_proc.stdout.strip())
    assert parent_payload["task_id"] == parent_id

    # Create child with --parent
    child_id = "200.1-wave1-child"
    child_proc = run(
        "task",
        "new",
        ["--id", "200.1", "--wave", "wave1", "--slug", "child", "--parent", parent_id, "--json"],
        env,
    )
    child_payload = json.loads(child_proc.stdout.strip())
    assert child_payload["task_id"] == child_id

    from edison.core.utils.text import parse_frontmatter

    child_path = root / str(child_payload["path"])
    parent_path = root / str(parent_payload["path"])
    assert child_path.exists()
    assert parent_path.exists()

    child_fm = parse_frontmatter(child_path.read_text(encoding="utf-8")).frontmatter
    child_edges = {(e["type"], e["target"]) for e in (child_fm.get("relationships") or [])}
    assert ("parent", parent_id) in child_edges

    parent_fm = parse_frontmatter(parent_path.read_text(encoding="utf-8")).frontmatter
    parent_edges = {(e["type"], e["target"]) for e in (parent_fm.get("relationships") or [])}
    assert ("child", child_id) in parent_edges


def test_task_split_accepts_children_alias(tmp_path: Path) -> None:
    """Docs/guidelines use `--children`; CLI must accept it as an alias for `--count`."""
    root = make_project_root(tmp_path)
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    parent_id = "300-wave1-parent"
    run("task", "new", ["--id", "300", "--wave", "wave1", "--slug", "parent", "--json"], env)

    proc = run("task", "split", [parent_id, "--children", "3", "--dry-run", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    assert payload["dry_run"] is True
    assert payload["parent_id"] == parent_id
    assert payload["count"] == 3
    assert len(payload["child_ids"]) == 3


def test_tasks_link_updates_session_graph(tmp_path: Path):
    root = make_project_root(tmp_path)
    parent = root / ".project" / "tasks" / "todo" / "200-wave1-demo.md"
    child = root / ".project" / "tasks" / "todo" / "200.1-wave1-child.md"
    parent.write_text("""---
id: "200-wave1-demo"
title: "Parent Task"
state: "todo"
---

# Parent Task
""")
    child.write_text("""---
id: "200.1-wave1-child"
title: "Child Task"
state: "todo"
---

# Child Task
""")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("task", "link", ["200-wave1-demo", "200.1-wave1-child", "--session", "s123", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["sessionId"] == "s123"
    # Single source of truth: task files must reflect the relationship.
    from edison.core.utils.text import parse_frontmatter

    updated_parent_fm = parse_frontmatter(parent.read_text()).frontmatter
    updated_child_fm = parse_frontmatter(child.read_text()).frontmatter

    parent_edges = {(e["type"], e["target"]) for e in (updated_parent_fm.get("relationships") or [])}
    child_edges = {(e["type"], e["target"]) for e in (updated_child_fm.get("relationships") or [])}
    assert ("child", "200.1-wave1-child") in parent_edges
    assert ("parent", "200-wave1-demo") in child_edges


def test_tasks_new_creates_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_task_template(root)
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    proc = run("task", "new", ["--id", "150", "--wave", "wave1", "--slug", "demo", "--json"], env)
    payload = json.loads(proc.stdout.strip())
    path = root / payload["path"]
    assert path.exists()
    content = path.read_text()
    assert "150-wave1-demo" in content


def test_tasks_status_moves_file(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_path = root / ".project" / "tasks" / "todo" / "150-wave1-demo.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    # Create proper task file with YAML frontmatter
    task_path.write_text("""---
id: "150-wave1-demo"
title: "Demo Task"
state: "todo"
---

# Demo Task

Demo description
""")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    run("task", "status", ["150-wave1-demo", "--status", "wip", "--force", "--json"], env)
    moved = root / ".project" / "tasks" / "wip" / "150-wave1-demo.md"
    assert moved.exists()


def test_tasks_ready_moves_wip_to_done(tmp_path: Path):
    root = make_project_root(tmp_path)
    task_id = "150-wave1-demo"

    # Ensure the session exists (session-scoped commands must fail-closed).
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=root)
    repo.create(Session.create("s1", owner="alice", state="wip"))

    # session scoped wip task + qa waiting
    wip_task = root / ".project" / "sessions" / "wip" / "s1" / "tasks" / "wip"
    wip_task.mkdir(parents=True, exist_ok=True)
    wip_path = wip_task / f"{task_id}.md"
    wip_path.write_text(f"""---
id: "{task_id}"
title: "Demo Task"
state: "wip"
session_id: "s1"
---

# Demo Task

Demo description
""")

    qa_waiting = root / ".project" / "sessions" / "wip" / "s1" / "qa" / "waiting"
    qa_waiting.mkdir(parents=True, exist_ok=True)
    qa_wait_path = qa_waiting / f"{task_id}-qa.md"
    qa_wait_path.write_text(f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA for {task_id}"
state: "waiting"
round: 1
session_id: "s1"
---

# QA for {task_id}

Validation scope
""")

    # evidence files
    evidence = root / ".project" / "qa" / "validation-reports" / task_id / "round-1"
    evidence.mkdir(parents=True, exist_ok=True)
    # Guard can_finish_task requires a non-empty implementation report.
    (evidence / "implementation-report.md").write_text(
        """---
filesChanged:
  - src/demo.ts
---
""",
        encoding="utf-8",
    )

    # Command evidence is repo-scoped and stored as snapshots (not per-round).
    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.qa.evidence.snapshots import SnapshotKey, snapshot_dir
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    fp = compute_repo_fingerprint(root)
    key = SnapshotKey.from_fingerprint(fp)
    snap = snapshot_dir(project_root=root, key=key)
    for filename, cmd_name in [
        ("command-type-check.txt", "type-check"),
        ("command-lint.txt", "lint"),
        ("command-test.txt", "test"),
        ("command-build.txt", "build"),
    ]:
        write_command_evidence(
            path=snap / filename,
            task_id=task_id,
            round_num=0,
            command_name=cmd_name,
            command="true",
            cwd=str(root),
            exit_code=0,
            output="ok\n",
            fingerprint=fp,
        )

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    run("task", "ready", [task_id, "--session", "s1", "--json"], env)

    # Task should be moved to done state
    done_path = root / ".project" / "sessions" / "wip" / "s1" / "tasks" / "done" / f"{task_id}.md"
    # QA should be promoted to todo state
    qa_todo = root / ".project" / "sessions" / "wip" / "s1" / "qa" / "todo" / f"{task_id}-qa.md"
    assert done_path.exists(), f"Expected task at {done_path}"
    assert qa_todo.exists(), f"Expected QA at {qa_todo}"


def test_qa_bundle_outputs_manifest(tmp_path: Path):
    root = make_project_root(tmp_path)
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    # Ensure the session exists (explicit --session must be validated + exist).
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=root)
    repo.create(Session.create("s1", owner="alice", state="wip"))

    # register tasks in session graph
    from edison.core.session import graph as session_graph
    os.environ["AGENTS_PROJECT_ROOT"] = str(root)
    # Session graph linking updates task files; ensure the tasks exist.
    tasks_done = root / ".project" / "tasks" / "done"
    tasks_done.mkdir(parents=True, exist_ok=True)
    (tasks_done / "150-wave1-demo.md").write_text(
        "---\nid: \"150-wave1-demo\"\ntitle: \"Demo Task\"\nstate: \"done\"\n---\n\n# Demo Task\n",
        encoding="utf-8",
    )
    (tasks_done / "150.1-wave1-child.md").write_text(
        "---\nid: \"150.1-wave1-child\"\ntitle: \"Child Task\"\nstate: \"done\"\n---\n\n# Child Task\n",
        encoding="utf-8",
    )
    session_graph.register_task("s1", "150-wave1-demo", owner="alice", status="done")
    session_graph.register_task("s1", "150.1-wave1-child", owner="alice", status="done")
    session_graph.link_tasks("s1", "150-wave1-demo", "150.1-wave1-child")

    result = run("qa", "bundle", ["150-wave1-demo", "--session", "s1", "--json"], env)
    payload = json.loads(result.stdout.strip())
    assert payload["sessionId"] == "s1"
    assert payload["rootTask"] == "150-wave1-demo"
    assert isinstance(payload["tasks"], list)


def test_qa_promote_moves_state(tmp_path: Path):
    root = make_project_root(tmp_path)
    # Guard can_start_qa requires the task be in done/validated.
    task_id = "150-wave1-demo"
    task_done_dir = root / ".project" / "tasks" / "done"
    task_done_dir.mkdir(parents=True, exist_ok=True)
    (task_done_dir / f"{task_id}.md").write_text(
        f"""---
id: "{task_id}"
title: "Demo Task"
state: "done"
---

# Demo Task

Done.
""",
        encoding="utf-8",
    )
    qa_waiting_dir = root / ".project" / "qa" / "waiting"
    qa_waiting_dir.mkdir(parents=True, exist_ok=True)
    qa_waiting = qa_waiting_dir / f"{task_id}-qa.md"
    qa_waiting.write_text("""---
id: "150-wave1-demo-qa"
task_id: "150-wave1-demo"
title: "QA for 150-wave1-demo"
state: "waiting"
round: 1
---

# QA for 150-wave1-demo

Validation scope
""")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    run("qa", "promote", [task_id, "--status", "todo", "--json"], env)
    qa_todo = root / ".project" / "qa" / "todo" / f"{task_id}-qa.md"
    assert qa_todo.exists()


def test_guidelines_audit_writes_evidence(tmp_path: Path):
    root = make_project_root(tmp_path)
    # create a project-level guideline file (NOT .edison/core/ - that is legacy)
    gdir = root / ".edison" / "guidelines"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "project-guideline.md").write_text("Project guideline text")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    result = run("qa", "audit", ["--json"], env)
    summary = json.loads(result.stdout.strip())
    evidence_root = root / ".project" / "qa" / "validation-reports" / "fix-9-guidelines-audit"
    assert summary["duplication"]["pairs_found"] >= 0
    assert (evidence_root / "summary.json").exists()
