"""Tests for directory creation in task workflow operations.

This file tests that task and QA workflow operations properly create
directories when needed. Tests real filesystem operations without mocks.

Following CRITICAL PRINCIPLES:
- NO MOCKS: Test real behavior, real code, real libs
- Test actual mkdir operations with real filesystem
- Use isolated_project_env fixture for test isolation
"""
from __future__ import annotations
from helpers.io_utils import write_yaml

import pytest
from pathlib import Path

from edison.core.task.workflow import TaskQAWorkflow
from edison.core.task.repository import TaskRepository
from edison.core.qa.workflow.repository import QARepository
from edison.core.task.models import Task
from edison.core.qa.models import QARecord
from edison.core.entity import EntityMetadata
from edison.core.utils.io.locking import safe_move_file, write_text_locked
from edison.core.config import get_semantic_state

@pytest.fixture
def task_env(tmp_path, monkeypatch):
    """Setup task workflow environment with real configuration."""
    repo = tmp_path
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"

    # 1. defaults.yaml (State Machine + Semantics)
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}]},
                        "done": {"allowed_transitions": [{"to": "validated"}]},
                        "validated": {"allowed_transitions": []},
                    },
                },
                "qa": {
                    "states": {
                        "waiting": {"allowed_transitions": [{"to": "todo"}]},
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}]},
                        "done": {"allowed_transitions": [{"to": "validated"}]},
                        "validated": {"allowed_transitions": []},
                    }
                }
            },
            "semantics": {
                "task": {
                    "todo": "todo",
                    "wip": "wip",
                    "done": "done",
                    "validated": "validated",
                },
                "qa": {
                    "waiting": "waiting",
                    "todo": "todo",
                    "wip": "wip",
                    "done": "done",
                    "validated": "validated",
                },
            },
        },
    )

    # 2. tasks.yaml
    write_yaml(
        config_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                },
            }
        },
    )

    # 3. session.yaml (for session paths)
    write_yaml(
        config_dir / "session.yaml",
        {
            "session": {
                "paths": {
                    "root": ".edison/sessions",
                    "archive": ".edison/sessions/archive",
                    "template": ".edison/sessions/TEMPLATE.json",
                }
            }
        }
    )

    # Set environment and clear caches
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Create session directory structure (sessions live in .project/sessions per ManagementPaths)
    (repo / ".project" / "sessions" / "wip").mkdir(parents=True, exist_ok=True)

    return repo

# ----------------------------------------------------------------------
# Tests for TaskQAWorkflow directory creation
# ----------------------------------------------------------------------

def test_create_task_ensures_task_directory(task_env):
    """Verify create_task creates task directory structure."""
    workflow = TaskQAWorkflow(project_root=task_env)

    # Create task - should create .project/tasks/todo/ directory
    task = workflow.create_task(
        task_id="T-001",
        title="Test task",
        description="Test description",
        create_qa=False,  # Don't create QA for this test
    )

    # Verify task file exists
    task_file = task_env / ".project" / "tasks" / "todo" / "T-001.md"
    assert task_file.exists(), "Task file should be created"
    assert task_file.parent.exists(), "Task directory should exist"
    assert task_file.parent.name == "todo", "Task should be in todo directory"

    # Verify content (Task ID is in HTML comment format)
    content = task_file.read_text(encoding="utf-8")
    assert "Test task" in content, "Task file should contain title"
    assert "Test description" in content, "Task file should contain description"

def test_create_task_ensures_qa_directory(task_env):
    """Verify create_task creates QA directory structure."""
    workflow = TaskQAWorkflow(project_root=task_env)

    # Create task with QA
    task = workflow.create_task(
        task_id="T-002",
        title="Test task with QA",
        create_qa=True,
    )

    # Verify QA file exists (QA ID is task_id + "-qa", filename is qa_id + ".md")
    qa_file = task_env / ".project" / "qa" / "waiting" / "T-002-qa.md"
    assert qa_file.exists(), "QA file should be created"
    assert qa_file.parent.exists(), "QA directory should exist"
    assert qa_file.parent.name == "waiting", "QA should be in waiting directory"

def test_claim_task_ensures_session_directories(task_env):
    """Verify claim_task creates session task and QA directories."""
    workflow = TaskQAWorkflow(project_root=task_env)

    # Create task first
    workflow.create_task(
        task_id="T-003",
        title="Task to claim",
        create_qa=True,
    )

    # Create session directory and metadata (sessions live in .project/sessions per ManagementPaths)
    session_id = "test-session-001"
    session_dir = task_env / ".project" / "sessions" / "wip" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal session.json
    import json
    session_file = session_dir / "session.json"
    session_file.write_text(
        json.dumps({
            "meta": {
                "sessionId": session_id,
                "status": "wip",
                "owner": "test",
            },
            "tasks": {},
        }),
        encoding="utf-8"
    )

    # Claim task - should move to session directories
    task = workflow.claim_task(task_id="T-003", session_id=session_id)

    # Verify session task directory was created
    session_task_dir = session_dir / "tasks" / "wip"
    assert session_task_dir.exists(), "Session task directory should be created"

    # Verify task file is in session
    session_task_file = session_task_dir / "T-003.md"
    assert session_task_file.exists(), "Task should be moved to session directory"

    # Verify session QA directory was created (QA stays in "waiting" state when claimed)
    session_qa_dir = session_dir / "qa" / "waiting"
    assert session_qa_dir.exists(), "Session QA directory should be created"

    # Verify QA file is in session (QA ID is task_id + "-qa")
    session_qa_file = session_qa_dir / "T-003-qa.md"
    assert session_qa_file.exists(), "QA should be moved to session directory"

def test_complete_task_ensures_done_directories(task_env):
    """Verify complete_task creates done directories."""
    workflow = TaskQAWorkflow(project_root=task_env)

    # Setup: Create and claim a task
    workflow.create_task(
        task_id="T-004",
        title="Task to complete",
        create_qa=True,
    )

    session_id = "test-session-002"
    session_dir = task_env / ".project" / "sessions" / "wip" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    import json
    session_file = session_dir / "session.json"
    session_file.write_text(
        json.dumps({
            "meta": {"sessionId": session_id, "status": "wip", "owner": "test"},
            "tasks": {},
        }),
        encoding="utf-8"
    )

    workflow.claim_task(task_id="T-004", session_id=session_id)

    # Complete task - should move to done directories
    task = workflow.complete_task(task_id="T-004", session_id=session_id)

    # Verify session done directories were created
    session_task_done = session_dir / "tasks" / "done"
    assert session_task_done.exists(), "Session task done directory should be created"

    task_file = session_task_done / "T-004.md"
    assert task_file.exists(), "Task should be in done directory"

    # When task is completed, QA transitions from "waiting" -> "todo" (ready for validation)
    session_qa_todo = session_dir / "qa" / "todo"
    assert session_qa_todo.exists(), "Session QA todo directory should be created"

    # QA ID is task_id + "-qa"
    qa_file = session_qa_todo / "T-004-qa.md"
    assert qa_file.exists(), "QA should be in todo directory (ready for validation)"

# ----------------------------------------------------------------------
# Tests for TaskRepository directory creation
# ----------------------------------------------------------------------

def test_repository_save_ensures_directory(task_env):
    """Verify TaskRepository.save creates parent directory."""
    repo = TaskRepository(project_root=task_env)

    # Create task entity
    task = Task(
        id="T-005",
        state="todo",
        title="Repository test",
        metadata=EntityMetadata.create(created_by="test")
    )

    # Save should create directory
    repo.save(task)

    # Verify directory and file exist
    task_file = task_env / ".project" / "tasks" / "todo" / "T-005.md"
    assert task_file.exists(), "Task file should be created"
    assert task_file.parent.exists(), "Parent directory should be created"

def test_repository_save_creates_nested_session_directories(task_env):
    """Verify TaskRepository creates nested session directories."""
    repo = TaskRepository(project_root=task_env)

    session_id = "deep-session-001"

    # Create task for session
    task = Task(
        id="T-006",
        state="wip",
        title="Session nested test",
        session_id=session_id,
        metadata=EntityMetadata.create(created_by="test", session_id=session_id)
    )

    # Save should create full session path
    repo.save(task)

    # Verify nested session directories were created (sessions in .project/sessions per ManagementPaths)
    expected_path = (
        task_env / ".project" / "sessions" / "wip" / session_id / "tasks" / "wip" / "T-006.md"
    )
    assert expected_path.exists(), "Task file should be created in session"

    # Verify all parent directories exist
    current = expected_path.parent
    while current != task_env:
        assert current.exists(), f"Directory {current} should exist"
        current = current.parent

# ----------------------------------------------------------------------
# Tests for QARepository directory creation
# ----------------------------------------------------------------------

def test_qa_repository_save_ensures_directory(task_env):
    """Verify QARepository.save creates parent directory."""
    qa_repo = QARepository(project_root=task_env)

    # Create QA record (requires id, task_id, state, title)
    qa = QARecord(
        id="T-007-qa",
        task_id="T-007",
        state="waiting",
        title="QA for T-007",
        metadata=EntityMetadata.create(created_by="test")
    )

    # Save should create directory
    qa_repo.save(qa)

    # Verify directory and file exist (filename is qa_id + ".md")
    qa_file = task_env / ".project" / "qa" / "waiting" / "T-007-qa.md"
    assert qa_file.exists(), "QA file should be created"
    assert qa_file.parent.exists(), "Parent directory should be created"

# ----------------------------------------------------------------------
# Tests for locking module directory creation
# ----------------------------------------------------------------------

def test_safe_move_file_ensures_dest_directory(task_env):
    """Verify safe_move_file creates destination directory."""
    # Create source file
    src = task_env / "source.txt"
    src.write_text("test content", encoding="utf-8")

    # Move to nested destination (directory doesn't exist yet)
    dest = task_env / "nested" / "dir" / "dest.txt"

    # safe_move_file should create parent directories
    result = safe_move_file(src, dest, repo_root=task_env)

    assert result == dest, "Should return destination path"
    assert dest.exists(), "Destination file should exist"
    assert dest.parent.exists(), "Destination directory should be created"
    assert not src.exists(), "Source file should be moved (not copied)"
    assert dest.read_text(encoding="utf-8") == "test content", "Content should be preserved"

def test_safe_move_file_creates_multiple_nested_levels(task_env):
    """Verify safe_move_file creates deeply nested directories."""
    src = task_env / "file.txt"
    src.write_text("nested test", encoding="utf-8")

    # Very deep nesting
    dest = task_env / "a" / "b" / "c" / "d" / "e" / "file.txt"

    safe_move_file(src, dest, repo_root=task_env)

    assert dest.exists(), "File should exist at deep path"
    # Verify all intermediate directories were created
    for level in ["a", "a/b", "a/b/c", "a/b/c/d", "a/b/c/d/e"]:
        dir_path = task_env / level
        assert dir_path.exists(), f"Directory {level} should be created"
        assert dir_path.is_dir(), f"{level} should be a directory"

def test_write_text_locked_ensures_directory(task_env):
    """Verify write_text_locked creates parent directory."""
    # Target file in non-existent directory
    target = task_env / "locked" / "subdir" / "file.txt"

    # write_text_locked should create parent directories
    write_text_locked(target, "locked content")

    assert target.exists(), "File should be created"
    assert target.parent.exists(), "Parent directory should be created"
    assert target.read_text(encoding="utf-8") == "locked content", "Content should match"

def test_write_text_locked_creates_nested_directories(task_env):
    """Verify write_text_locked creates deeply nested directories."""
    target = task_env / "level1" / "level2" / "level3" / "locked.txt"

    write_text_locked(target, "deeply nested")

    assert target.exists(), "File should exist"
    assert target.parent.exists(), "Parent directory should exist"

    # Verify all levels were created
    assert (task_env / "level1").is_dir()
    assert (task_env / "level1" / "level2").is_dir()
    assert (task_env / "level1" / "level2" / "level3").is_dir()

# ----------------------------------------------------------------------
# Edge cases and error conditions
# ----------------------------------------------------------------------

def test_directory_creation_with_existing_directories(task_env):
    """Verify operations work correctly when directories already exist."""
    workflow = TaskQAWorkflow(project_root=task_env)

    # Pre-create the directory structure
    todo_dir = task_env / ".project" / "tasks" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)

    # Should work fine even with existing directory
    task = workflow.create_task(
        task_id="T-008",
        title="Existing dir test",
        create_qa=False,
    )

    task_file = todo_dir / "T-008.md"
    assert task_file.exists(), "Should create file in existing directory"

def test_concurrent_directory_creation_safety(task_env):
    """Verify directory creation is safe for concurrent operations."""
    # This tests that mkdir(parents=True, exist_ok=True) pattern is used
    target_dir = task_env / "concurrent" / "test"

    # Multiple attempts to create same directory should all succeed
    for i in range(5):
        target = target_dir / f"file{i}.txt"
        write_text_locked(target, f"content {i}")
        assert target.exists()

    # All files should exist
    assert len(list(target_dir.glob("*.txt"))) == 5
