"""Tests for task state guards."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from helpers.command_runner import run_script, assert_command_failure, assert_command_success, assert_json_output
from helpers.env import TestProjectDir
from tests.helpers.paths import get_repo_root
from tests.helpers.timeouts import THREAD_JOIN_TIMEOUT


@pytest.fixture()
def project(tmp_path: Path) -> TestProjectDir:
    # Determine repo root (tests live under repository tests/ tree)
    repo_root = get_repo_root()
    proj = TestProjectDir(tmp_path, repo_root)
    # Ensure task and QA templates exist for CLI scripts
    tasks_tpl_src = repo_root / ".project" / "tasks" / "TEMPLATE.md"
    qa_tpl_src = repo_root / ".project" / "qa" / "TEMPLATE.md"
    tasks_tpl_dst = proj.project_root / "tasks" / "TEMPLATE.md"
    qa_tpl_dst = proj.project_root / "qa" / "TEMPLATE.md"
    if tasks_tpl_src.exists():
        tasks_tpl_dst.write_text(tasks_tpl_src.read_text())
    else:
        tasks_tpl_dst.write_text(
            """# Task: PPP-waveN-slug

## Metadata
- **Task ID:** PPP-waveN-slug
- **Priority Slot:** PPP
- **Wave:** waveN
- **Task Type:** (ui-component | api-route | database-schema | test-suite | refactoring | full-stack-feature | ...)
- **Owner:** _unassigned_
- **Status:** todo | wip | done | validated
- **Created:** YYYY-MM-DD
- **Parent Task:** _none_
- **Continuation ID:** _none_
"""
        )
    if qa_tpl_src.exists():
        qa_tpl_dst.write_text(qa_tpl_src.read_text())
    else:
        qa_tpl_dst.write_text(
            """# PPP-waveN-slug-qa

## Metadata
- **Validator Owner:** _unassigned_
- **Status:** waiting | todo | wip | done | validated
- **Created:** YYYY-MM-DD
- **Evidence Directory:** `.project/qa/validation-evidence/task-XXXX/`
"""
        )
    return proj


def _create_create_env(owner: str = "tester") -> dict:
    return {"AGENTS_OWNER": owner}


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.security
@pytest.mark.task
def test_claim_disallows_done_bypass(project: TestProjectDir):
    # Arrange: create a new task in todo
    res_new = run_script(
        "tasks/new",
        ["--id", "300", "--wave", "wave1", "--slug", "guard-claim"],
        cwd=project.tmp_path,
        env=_create_env(),
    )
    assert_command_success(res_new)
    task_id = "300-wave1-guard-claim"
    assert project.get_task_state(task_id) == "todo"

    # Act: attempt to bypass guards by claiming directly to done
    res_claim = run_script(
        "tasks/claim",
        [task_id, "--status", "done"],
        cwd=project.tmp_path,
        env=_create_env(),
    )

    # Assert: must fail-closed and remain out of done
    assert_command_failure(res_claim)
    assert project.get_task_state(task_id) != "done"


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.security
@pytest.mark.qa
def test_status_never_synthesizes_approval(project: TestProjectDir):
    # Arrange: create task + a minimal QA file marked as done (no evidence)
    res_new = run_script(
        "tasks/new",
        ["--id", "301", "--wave", "wave1", "--slug", "guard-validate"],
        cwd=project.tmp_path,
        env=_create_env(),
    )
    assert_command_success(res_new)
    task_id = "301-wave1-guard-validate"

    # Place the task directly in tasks/done (simulate implementation finished)
    todo_path = project.project_root / "tasks" / "todo" / f"{task_id}.md"
    done_dir = project.project_root / "tasks" / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    done_path = done_dir / f"{task_id}.md"
    content = todo_path.read_text()
    content = content.replace("**Status:** todo", "**Status:** done")
    done_path.write_text(content)
    todo_path.unlink(missing_ok=True)

    # Create minimal QA file directly in qa/done/ to trigger status validation path
    qa_done_dir = project.project_root / "qa" / "done"
    qa_done_dir.mkdir(parents=True, exist_ok=True)
    (qa_done_dir / f"{task_id}-qa.md").write_text("# QA\n- **Status:** done\n")

    # Act: attempt to promote task to validated (validators/validate will fail)
    res_validate = run_script(
        "tasks/status",
        [task_id, "--status", "validated"],
        cwd=project.tmp_path,
        env=_create_env(),
    )

    # Assert: must fail (no synthetic approval), and no bundle-approved.md is created
    assert_command_failure(res_validate)
    evidence_dir = project.project_root / "qa" / "validation-evidence" / task_id
    # No evidence rounds should exist as a side effect
    assert not any(evidence_dir.glob("round-*/bundle-approved.md"))
    # Task must not be in validated
    assert project.get_task_state(task_id) != "validated"


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.security
@pytest.mark.task
def test_allocate_id_considers_session_scoped_siblings(project: TestProjectDir):
    # Arrange: parent base 201, create an existing child 201.1 under a session
    res_parent = run_script(
        "tasks/new",
        ["--id", "201", "--wave", "wave1", "--slug", "parent"],
        cwd=project.tmp_path,
        env=_create_env(),
    )
    assert_command_success(res_parent)
    # Create a child in session sA manually in session-scoped tree
    sess_child_dir = project.project_root / "sessions" / "wip" / "sA" / "tasks" / "todo"
    sess_child_dir.mkdir(parents=True, exist_ok=True)
    (sess_child_dir / "201.1-wave1-child-a.md").write_text(
        "- **Status:** todo\n- **Owner:** tester\n"
    )

    # Act: allocate next child id for base 201
    res_alloc = run_script(
        "tasks/allocate-id",
        ["--parent", "201"],
        cwd=project.tmp_path,
        env=_create_env(),
    )

    # Assert: next id must be 201.2 (not 201.1 duplicate)
    assert_command_success(res_alloc)
    next_id = res_alloc.stdout.strip().splitlines()[-1]
    assert next_id == "201.2"


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.security
@pytest.mark.task
def test_ensure_followups_avoids_duplicate_ids_with_session_siblings(project: TestProjectDir):
    # Arrange: parent 202, existing session-scoped child 202.1
    res_parent = run_script(
        "tasks/new",
        ["--id", "202", "--wave", "wave1", "--slug", "parent-fu"],
        cwd=project.tmp_path,
        env=_create_env(),
    )
    assert_command_success(res_parent)
    task_id = "202-wave1-parent-fu"
    run_script(
        "tasks/new",
        ["--id", "202.1", "--wave", "wave1", "--slug", "child-existing", "--session", "sFU"],
        cwd=project.tmp_path,
        env=_create_env(),
    )

    # Seed implementation-report.md to request a blocking follow-up
    round_dir = project.project_root / "qa" / "validation-evidence" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "implementation-report.md").write_text(
        """---
followUpTasks:
  - title: "blocking-child"
    blockingBeforeValidation: true
---
""",
        encoding="utf-8",
    )

    # Act: enforce follow-up creation
    res_fus = run_script(
        "tasks/ensure-followups",
        ["--task", task_id, "--session", "sFU", "--enforce"],
        cwd=project.tmp_path,
        env=_create_env(),
    )
    data = assert_json_output(res_fus)

    # Assert: created child should be 202.2 (not colliding with 202.1 in session scope)
    created = data.get("created") or []
    assert any(cid.startswith("202.2-") for cid in created), f"unexpected created IDs: {created}"


@pytest.mark.security
def test_write_text_locked_atomic_replace_used(project: TestProjectDir):
    """Test that write_text_locked uses atomic replacement.

    This test verifies that write_text_locked creates a temp file and atomically
    replaces the target, ensuring no partial writes are visible. We test this by
    verifying that concurrent reads always see either the old or new content,
    never partial/corrupted content.
    """
    from edison.core.utils.io.locking import write_text_locked
    import threading

    target = project.tmp_path / "atomic.txt"
    target.write_text("original content\n")

    errors: list[BaseException] = []
    stop_event = threading.Event()
    iterations_completed = {"count": 0}

    def writer():
        """Continuously write to the file."""
        try:
            counter = 0
            while not stop_event.is_set() and counter < 50:
                write_text_locked(target, f"updated content {counter}\n")
                counter += 1
            iterations_completed["count"] = counter
        except BaseException as e:
            errors.append(e)

    def reader():
        """Continuously read and validate the file content."""
        try:
            for _ in range(100):
                if stop_event.is_set():
                    break
                content = target.read_text()
                # Verify content is always a complete line (never partial)
                assert content.endswith("\n"), f"Partial write detected: {content!r}"
                # Verify content matches expected pattern (either original or updated)
                assert (
                    content.startswith("original content") or
                    content.startswith("updated content")
                ), f"Corrupted content: {content!r}"
        except BaseException as e:
            errors.append(e)

    # Start writer and readers concurrently
    writer_thread = threading.Thread(target=writer, daemon=True)
    reader_threads = [threading.Thread(target=reader, daemon=True) for _ in range(3)]

    writer_thread.start()
    for t in reader_threads:
        t.start()

    # Wait for completion
    writer_thread.join(timeout=THREAD_JOIN_TIMEOUT)
    stop_event.set()
    for t in reader_threads:
        t.join(timeout=THREAD_JOIN_TIMEOUT / 2)

    # Verify no errors occurred
    assert not errors, f"Encountered errors during concurrent read/write: {errors!r}"
    # Verify writes actually happened
    assert iterations_completed["count"] > 0, "Writer did not complete any iterations"
    # Final content should be valid
    final_content = target.read_text()
    assert final_content.endswith("\n")
