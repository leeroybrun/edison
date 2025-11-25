"""Test 03: QA Lifecycle

Tests for QA creation, validation workflow, and state transitions using REAL CLIs.

Test Coverage:
- QA creation via real `qa/new` CLI
- QA state transitions using real `qa/status` CLI
- QA-session integration
- QA-task relationship validation

IMPORTANT: These tests execute REAL CLI commands, NOT mock data.
All behaviors must match guidelines in .agents/guidelines/*.md
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from helpers import TestProjectDir
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
)
from helpers.assertions import (
    assert_file_exists,
    assert_file_contains,
)


@pytest.mark.qa
@pytest.mark.fast
def test_create_qa_file(test_project_dir: TestProjectDir):
    """✅ CORRECT: Create QA file using REAL qa/new CLI.

    Per guidelines: QA files created via `qa/new <task-id>`.
    """
    task_num = "100"
    wave = "wave1"
    slug = "test-qa"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create task via helper (avoids missing legacy wrappers)
    test_project_dir.create_task(task_id, wave=wave, slug=slug, state="todo")

    # Create QA via REAL CLI (creates in qa/waiting/ per guidelines)
    qa_result = run_script(
        "qa/new",
        [task_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(qa_result)

    # Verify QA file was created in qa/waiting/ (NOT qa/todo/)
    qa_path = test_project_dir.project_root / "qa" / "waiting" / f"{task_id}-qa.md"
    assert_file_exists(qa_path)

    # Verify QA content has required fields
    from helpers.assertions import read_file
    qa_content = read_file(qa_path)
    assert f"# {task_id}-qa" in qa_content, "QA should have title with ID"
    assert task_id in qa_content, "QA should reference parent task ID"


@pytest.mark.qa
@pytest.mark.session
@pytest.mark.fast
def test_create_qa_with_session(test_project_dir: TestProjectDir):
    """✅ CORRECT: Create QA and register in session using REAL CLI.

    Per guidelines: QA files can be registered in sessions via --session parameter.
    """
    task_num = "150"
    wave = "wave1"
    slug = "qa-session"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-qa-session"

    # Create session directly via helper (avoids external deps)
    test_project_dir.create_session(session_id, state="wip")

    # Create task via helper (avoids missing legacy wrappers)
    test_project_dir.create_task(task_id, wave=wave, slug=slug, state="todo")

    # Create QA with session registration via REAL CLI
    qa_result = run_script(
        "qa/new",
        [task_id, "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(qa_result)

    # Verify QA was created
    qa_path = test_project_dir.project_root / "qa" / "waiting" / f"{task_id}-qa.md"
    assert_file_exists(qa_path)

    # Verify QA was registered in session JSON
    session_path = test_project_dir.project_root / "sessions" / "wip" / f"{session_id}.json"
    session_data = json.loads(session_path.read_text())
    qa_id = f"{task_id}-qa"
    assert qa_id in session_data["qa"], f"QA {qa_id} should be registered in session"


@pytest.mark.qa
@pytest.mark.fast
def test_qa_state_transitions(test_project_dir: TestProjectDir):
    """✅ CORRECT: Test QA state transitions using REAL qa/promote CLI.

    Per guidelines: Use `qa/promote --task <task-id> --to <state> [--session <sid>]` for QA transitions.
    Tests transitions:
    - waiting → todo (QA ready to start)
    - todo → wip (QA in progress)
    - wip → done (QA validation complete)
    """
    task_num = "200"
    wave = "wave1"
    slug = "qa-transitions"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-qa-transitions"

    # Create session directly via helper
    test_project_dir.create_session(session_id, state="wip")

    # Create task via helper
    test_project_dir.create_task(task_id, wave=wave, slug=slug, state="todo")

    # Create QA via REAL CLI (starts in waiting)
    qa_result = run_script(
        "qa/new",
        [task_id, "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(qa_result)

    # Verify QA is in waiting
    qa_path = test_project_dir.project_root / "qa" / "waiting" / f"{task_id}-qa.md"
    assert_file_exists(qa_path)

    # Satisfy guard: waiting→todo requires parent task in tasks/done or validated
    todo_task = test_project_dir.project_root / "tasks" / "todo" / f"{task_id}.md"
    done_task = test_project_dir.project_root / "tasks" / "done" / f"{task_id}.md"
    done_task.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join([f"# Task {task_id}", "", "- **Owner:** _unassigned_", "- **Status:** done"]) + "\n"
    done_task.write_text(content)
    try:
        todo_task.unlink()
    except FileNotFoundError:
        pass

    # Move to todo via qa/promote
    result = run_script(
        "qa/promote",
        ["--task", task_id, "--to", "todo", "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(result)

    # Verify moved to todo
    todo_path = test_project_dir.project_root / "qa" / "todo" / f"{task_id}-qa.md"
    assert_file_exists(todo_path)

    # Move to wip via qa/promote
    result = run_script(
        "qa/promote",
        ["--task", task_id, "--to", "wip", "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(result)

    # Verify moved to wip
    wip_path = test_project_dir.project_root / "qa" / "wip" / f"{task_id}-qa.md"
    assert_file_exists(wip_path)

    # Do not promote to done here; qa/promote enforces evidence. Done state covered elsewhere.


@pytest.mark.qa
@pytest.mark.fast
def test_qa_task_relationship(test_project_dir: TestProjectDir):
    """✅ CORRECT: Test QA-task relationship and naming convention.

    Per guidelines: QA files are named <task-id>-qa.md
    """
    task_num = "250"
    wave = "wave1"
    slug = "relationship"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create task via helper
    test_project_dir.create_task(task_id, wave=wave, slug=slug, state="todo")

    # Create QA via qa/new
    qa_result = run_script("qa/new", [task_id], cwd=test_project_dir.tmp_path)
    assert_command_success(qa_result)

    # Verify QA naming convention: <task-id>-qa.md
    qa_path = test_project_dir.project_root / "qa" / "waiting" / f"{task_id}-qa.md"
    assert_file_exists(qa_path)

    # Verify QA references parent task
    from helpers.assertions import read_file
    qa_content = read_file(qa_path)
    assert task_id in qa_content, "QA should reference parent task ID"
