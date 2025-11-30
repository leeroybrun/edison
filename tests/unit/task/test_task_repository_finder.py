"""Tests for TaskRepository finder methods.

These tests ensure TaskRepository provides the same functionality as
the legacy finder.py module for discovering tasks across filesystem.

Following strict TDD: These tests are written FIRST and MUST fail initially.
"""
from __future__ import annotations
from helpers.io_utils import write_yaml
from tests.helpers.fixtures import create_repo_with_git
from helpers.markdown_utils import create_markdown_task
from helpers.env_setup import setup_project_root

from pathlib import Path
import importlib
import pytest

from edison.core.task.repository import TaskRepository
from edison.core.entity import EntityMetadata, EntityNotFoundError
from edison.core.task.models import Task

def _bootstrap_repo(repo: Path) -> None:
    """Bootstrap a test repository with minimal config."""
    create_repo_with_git(repo)
    config_dir = repo / ".edison" / "config"
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
            }
        },
    )
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

@pytest.fixture
def repo_env(tmp_path, monkeypatch):
    """Setup a repository environment."""
    repo = tmp_path
    _bootstrap_repo(repo)

    setup_project_root(monkeypatch, repo)

    # Reload config-dependent modules
    import edison.core.config.domains.task as task_config
    importlib.reload(task_config)
    import edison.core.task.paths as paths
    importlib.reload(paths)

    return repo

# ========================================
# Test: find_by_state()
# ========================================

def test_find_by_state_returns_tasks_in_given_state(repo_env):
    """TaskRepository.find_by_state() returns all tasks in a specific state."""
    # Arrange: Create tasks in different states
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-1.md",
        "T-1", "Task One", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-2.md",
        "T-2", "Task Two", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "tasks" / "wip" / "T-3.md",
        "T-3", "Task Three", "wip"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act: Find tasks in 'todo' state
    tasks = repo.find_by_state("todo")

    # Assert
    assert len(tasks) == 2
    task_ids = {t.id for t in tasks}
    assert "T-1" in task_ids
    assert "T-2" in task_ids
    assert "T-3" not in task_ids

def test_find_by_state_returns_empty_list_when_state_dir_missing(repo_env):
    """TaskRepository.find_by_state() returns empty list when state dir doesn't exist."""
    repo = TaskRepository(project_root=repo_env)

    # Act: Find in non-existent state directory
    tasks = repo.find_by_state("done")

    # Assert
    assert tasks == []

def test_find_by_state_includes_session_tasks(repo_env):
    """TaskRepository.find_by_state() includes tasks from session directories."""
    # Arrange: Create global and session tasks in same state
    create_markdown_task(
        repo_env / ".project" / "tasks" / "wip" / "T-GLOBAL.md",
        "T-GLOBAL", "Global Task", "wip"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "wip" / "T-SESS.md",
        "T-SESS", "Session Task", "wip", "sess-1"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    tasks = repo.find_by_state("wip")

    # Assert: Should find both
    assert len(tasks) == 2
    task_ids = {t.id for t in tasks}
    assert "T-GLOBAL" in task_ids
    assert "T-SESS" in task_ids

# ========================================
# Test: find_all()
# ========================================

def test_find_all_returns_all_tasks_across_states(repo_env):
    """TaskRepository.find_all() returns all tasks from all states."""
    # Arrange: Create tasks in multiple states
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-1.md",
        "T-1", "Task One", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "tasks" / "wip" / "T-2.md",
        "T-2", "Task Two", "wip"
    )
    create_markdown_task(
        repo_env / ".project" / "tasks" / "done" / "T-3.md",
        "T-3", "Task Three", "done"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    tasks = repo.find_all()

    # Assert
    assert len(tasks) == 3
    task_ids = {t.id for t in tasks}
    assert "T-1" in task_ids
    assert "T-2" in task_ids
    assert "T-3" in task_ids

def test_find_all_includes_global_and_session_tasks(repo_env):
    """TaskRepository.find_all() includes tasks from both global and session dirs."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-G1.md",
        "T-G1", "Global 1", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "wip" / "T-S1.md",
        "T-S1", "Session 1", "wip", "sess-1"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-2" / "tasks" / "done" / "T-S2.md",
        "T-S2", "Session 2", "done", "sess-2"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    tasks = repo.find_all()

    # Assert
    assert len(tasks) == 3
    task_ids = {t.id for t in tasks}
    assert "T-G1" in task_ids
    assert "T-S1" in task_ids
    assert "T-S2" in task_ids

def test_find_all_returns_empty_list_when_no_tasks(repo_env):
    """TaskRepository.find_all() returns empty list when no tasks exist."""
    repo = TaskRepository(project_root=repo_env)

    # Act
    tasks = repo.find_all()

    # Assert
    assert tasks == []

# ========================================
# Test: find() with filters
# ========================================

def test_find_with_state_filter(repo_env):
    """TaskRepository.find(state=...) filters by state."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-1.md",
        "T-1", "Task One", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "tasks" / "wip" / "T-2.md",
        "T-2", "Task Two", "wip"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    tasks = repo.find(state="todo")

    # Assert
    assert len(tasks) == 1
    assert tasks[0].id == "T-1"

def test_find_with_session_id_filter(repo_env):
    """TaskRepository.find(session_id=...) filters by session."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-G.md",
        "T-G", "Global Task", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "wip" / "T-S1.md",
        "T-S1", "Session 1", "wip", "sess-1"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-2" / "tasks" / "wip" / "T-S2.md",
        "T-S2", "Session 2", "wip", "sess-2"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    tasks = repo.find(session_id="sess-1")

    # Assert
    assert len(tasks) == 1
    assert tasks[0].id == "T-S1"
    assert tasks[0].session_id == "sess-1"

def test_find_with_multiple_filters(repo_env):
    """TaskRepository.find() can combine multiple filters."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "todo" / "T-S1-TODO.md",
        "T-S1-TODO", "Session 1 Todo", "todo", "sess-1"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "wip" / "T-S1-WIP.md",
        "T-S1-WIP", "Session 1 Wip", "wip", "sess-1"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-2" / "tasks" / "todo" / "T-S2-TODO.md",
        "T-S2-TODO", "Session 2 Todo", "todo", "sess-2"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act: Find tasks in sess-1 with state=todo
    tasks = repo.find(session_id="sess-1", state="todo")

    # Assert
    assert len(tasks) == 1
    assert tasks[0].id == "T-S1-TODO"

def test_find_returns_empty_list_when_no_matches(repo_env):
    """TaskRepository.find() returns empty list when no tasks match criteria."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-1.md",
        "T-1", "Task One", "todo"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act: Search for non-existent session
    tasks = repo.find(session_id="nonexistent")

    # Assert
    assert tasks == []

# ========================================
# Test: get() - single task lookup
# ========================================

def test_get_finds_task_in_global_directory(repo_env):
    """TaskRepository.get() finds task in global directory."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-FIND-ME.md",
        "T-FIND-ME", "Find Me", "todo"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    task = repo.get("T-FIND-ME")

    # Assert
    assert task is not None
    assert task.id == "T-FIND-ME"
    assert task.title == "Find Me"

def test_get_finds_task_in_session_directory(repo_env):
    """TaskRepository.get() finds task in session directory."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "wip" / "T-SESS-FIND.md",
        "T-SESS-FIND", "Session Find", "wip", "sess-1"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act
    task = repo.get("T-SESS-FIND")

    # Assert
    assert task is not None
    assert task.id == "T-SESS-FIND"
    assert task.session_id == "sess-1"

def test_get_returns_none_when_task_not_found(repo_env):
    """TaskRepository.get() returns None when task doesn't exist."""
    repo = TaskRepository(project_root=repo_env)

    # Act
    task = repo.get("NONEXISTENT")

    # Assert
    assert task is None

def test_get_searches_all_states(repo_env):
    """TaskRepository.get() searches across all states."""
    # Arrange: Create tasks in different states with similar IDs
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-MULTI.md",
        "T-MULTI", "Multi Todo", "todo"
    )

    repo = TaskRepository(project_root=repo_env)

    # Act: Find without knowing state
    task = repo.get("T-MULTI")

    # Assert
    assert task is not None
    assert task.id == "T-MULTI"
    assert task.state == "todo"

# ========================================
# Test: Compatibility with finder.py behavior
# ========================================

def test_list_all_compatible_with_list_records(repo_env):
    """TaskRepository.get_all() provides similar output to finder.list_records()."""
    # Arrange
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-1.md",
        "T-1", "Task One", "todo"
    )
    create_markdown_task(
        repo_env / ".project" / "tasks" / "wip" / "T-2.md",
        "T-2", "Task Two", "wip"
    )
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "sess-x" / "tasks" / "done" / "T-3.md",
        "T-3", "Task Three", "done", "sess-x"
    )

    repo = TaskRepository(project_root=repo_env)
    tasks = repo.get_all()

    # Assert: Should find all 3 tasks (global + session)
    assert len(tasks) == 3

    # Assert: Should have correct IDs
    repo_ids = {t.id for t in tasks}
    assert repo_ids == {"T-1", "T-2", "T-3"}

    # Assert: Global tasks have no session_id
    global_tasks = [t for t in tasks if t.id in ("T-1", "T-2")]
    for t in global_tasks:
        assert t.session_id is None

    # Assert: Session task has correct session_id
    session_tasks = [t for t in tasks if t.id == "T-3"]
    assert len(session_tasks) == 1
    assert session_tasks[0].session_id == "sess-x"

def test_get_compatible_with_find_record(repo_env):
    """TaskRepository.get() finds tasks correctly in expected locations."""
    # Arrange
    task_id = "T-COMPAT"
    expected_path = repo_env / ".project" / "tasks" / "todo" / f"{task_id}.md"
    create_markdown_task(
        expected_path,
        task_id, "Compat Task", "todo"
    )

    repo = TaskRepository(project_root=repo_env)
    task = repo.get(task_id)

    # Assert: Should find the task
    assert task is not None
    assert task.id == task_id

    # Assert: File exists at expected location
    assert expected_path.exists()
    assert expected_path.stem == task_id
