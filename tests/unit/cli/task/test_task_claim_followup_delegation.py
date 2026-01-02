"""Tests for task claim followup and delegation hint output.

This module tests the task claim command's new output features:
- Default output includes 'Next' block with `edison session next <session-id>` command
- --show-delegation flag prints delegation hint
- JSON includes `nextCommands` (and `delegationSuggestion` when enabled)

TDD: RED phase - these tests should FAIL until implementation is complete.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.entity import EntityMetadata
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository
from tests.helpers.session import ensure_session


@pytest.fixture
def setup_task_for_claim(isolated_project_env: Path) -> tuple[Path, str, str]:
    """Set up a task ready to be claimed and a session to claim it into."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-task-001"
    session_id = "sess-claim-test-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task for Claim",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    return project_root, task_id, session_id


@pytest.mark.task
def test_task_claim_default_output_includes_next_block(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that default task claim output includes the 'Next' block with session next command."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-next-001"
    session_id = "sess-claim-next-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task for Next Block",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        json=False,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Verify the output includes the Next block
    assert "Next:" in out or "Next" in out
    assert f"edison session next {session_id}" in out
    # Verify delegation reminder is present
    assert "delegate" in out.lower()


@pytest.mark.task
def test_task_claim_default_output_includes_delegation_reminder(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that default task claim output includes a delegation reminder."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-reminder-001"
    session_id = "sess-claim-reminder-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task for Reminder",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        json=False,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Verify the delegation reminder is present
    assert "delegate" in out.lower()
    # Should mention tracking if implementing directly
    assert "track" in out.lower() or "implement" in out.lower()


@pytest.mark.task
def test_task_claim_show_delegation_flag_prints_hint(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that --show-delegation flag prints delegation hint."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-deleg-001"
    session_id = "sess-claim-deleg-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task for Delegation Hint",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        show_delegation=True,  # New flag
        json=False,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # When --show-delegation is used, output should include delegation suggestion
    assert "Delegation" in out or "delegation" in out
    # Should include info about model/role or fallback note
    assert ("model" in out.lower() or "role" in out.lower() or
            "orchestrator" in out.lower() or "pal" in out.lower().replace("principal", ""))


@pytest.mark.task
def test_task_claim_show_delegation_includes_fallback_note_when_no_hint(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that --show-delegation includes fallback note when Pal is unavailable or no hint matches."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-fallback-001"
    session_id = "sess-claim-fallback-001"

    # Create a task without specific patterns that would match delegation rules
    task = Task(
        id=task_id,
        state=todo,
        title="Simple Task Without Patterns",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        show_delegation=True,
        json=False,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Should include either a suggestion or a fallback note
    assert ("delegation" in out.lower() or "orchestrator" in out.lower() or
            "direct" in out.lower() or "no pattern" in out.lower())


@pytest.mark.task
def test_task_claim_json_includes_next_commands(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that JSON output includes nextCommands field."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-json-001"
    session_id = "sess-claim-json-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task for JSON Output",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        json=True,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    data = json.loads(out)

    # Verify nextCommands field is present
    assert "nextCommands" in data
    assert isinstance(data["nextCommands"], list)
    assert len(data["nextCommands"]) > 0

    # Should include session next command
    session_next_found = any("session next" in cmd for cmd in data["nextCommands"])
    assert session_next_found, f"Expected 'session next' in nextCommands: {data['nextCommands']}"


@pytest.mark.task
def test_task_claim_json_includes_delegation_suggestion_when_enabled(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that JSON output includes delegationSuggestion when --show-delegation is used."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-json-deleg-001"
    session_id = "sess-claim-json-deleg-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task for JSON Delegation",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        show_delegation=True,  # Enable delegation hint
        json=True,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    data = json.loads(out)

    # Verify delegationSuggestion field is present when --show-delegation is used
    assert "delegationSuggestion" in data
    # It should be a dict with at least 'suggested' key
    assert isinstance(data["delegationSuggestion"], dict)
    assert "suggested" in data["delegationSuggestion"]


@pytest.mark.task
def test_task_claim_json_omits_delegation_suggestion_by_default(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that JSON output does NOT include delegationSuggestion by default (without --show-delegation)."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    task_id = "test-claim-json-no-deleg-001"
    session_id = "sess-claim-json-no-deleg-001"

    task = Task(
        id=task_id,
        state=todo,
        title="Test Task Without Delegation",
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(task)
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=task_id,
        session=session_id,
        type="task",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        json=True,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    data = json.loads(out)

    # delegationSuggestion should NOT be present without --show-delegation
    assert "delegationSuggestion" not in data


@pytest.mark.qa
def test_qa_claim_default_output_includes_next_block(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that QA claim also includes the 'Next' block."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo_state = workflow.get_semantic_state("qa", "todo")
    task_done_state = workflow.get_semantic_state("task", "done")

    # First create a task to link the QA to
    task_repo = TaskRepository(project_root=project_root)
    task_id = "test-qa-claim-task-001"
    qa_id = task_id  # QA IDs match task IDs

    task = Task(
        id=task_id,
        state=task_done_state,
        title="Task for QA Claim Test",
        metadata=EntityMetadata.create(created_by="test"),
    )
    task_repo.save(task)

    # Create the QA record
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.qa.models import QARecord

    qa_repo = QARepository(project_root=project_root)
    qa = QARecord(
        id=qa_id,
        state=todo_state,
        task_id=task_id,
        title="QA for Task",
        metadata=EntityMetadata.create(created_by="test"),
    )
    qa_repo.save(qa)

    session_id = "sess-qa-claim-001"
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=qa_id,
        session=session_id,
        type="qa",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        json=False,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Verify the output includes the Next block
    assert "Next:" in out or "Next" in out
    assert f"edison session next {session_id}" in out


@pytest.mark.qa
def test_qa_claim_json_includes_next_commands(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that QA claim JSON output includes nextCommands field."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo_state = workflow.get_semantic_state("qa", "todo")
    task_done_state = workflow.get_semantic_state("task", "done")

    # First create a task to link the QA to
    task_repo = TaskRepository(project_root=project_root)
    task_id = "test-qa-claim-json-task-001"
    qa_id = task_id

    task = Task(
        id=task_id,
        state=task_done_state,
        title="Task for QA Claim JSON Test",
        metadata=EntityMetadata.create(created_by="test"),
    )
    task_repo.save(task)

    # Create the QA record
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.qa.models import QARecord

    qa_repo = QARepository(project_root=project_root)
    qa = QARecord(
        id=qa_id,
        state=todo_state,
        task_id=task_id,
        title="QA for Task JSON",
        metadata=EntityMetadata.create(created_by="test"),
    )
    qa_repo.save(qa)

    session_id = "sess-qa-claim-json-001"
    ensure_session(session_id, state="active")

    from edison.cli.task.claim import main as claim_main

    args = argparse.Namespace(
        record_id=qa_id,
        session=session_id,
        type="qa",
        owner="test-user",
        status=None,
        takeover=False,
        reason=None,
        json=True,
        repo_root=project_root,
    )
    rc = claim_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    data = json.loads(out)

    # Verify nextCommands field is present
    assert "nextCommands" in data
    assert isinstance(data["nextCommands"], list)
