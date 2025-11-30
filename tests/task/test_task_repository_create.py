"""Tests for TaskQAWorkflow.create_task() method.

These tests ensure that TaskQAWorkflow implements task creation
with proper QA record creation following the legacy io.create_task behavior.

Following STRICT TDD - tests written FIRST, implementation second.
"""
from __future__ import annotations
from helpers.io_utils import write_yaml

import pytest
import importlib
from pathlib import Path
from edison.core.task.workflow import TaskQAWorkflow
from edison.core.task.repository import TaskRepository
from edison.core.qa.workflow.repository import QARepository
from edison.core.entity import PersistenceError, EntityMetadata
from edison.core.task.models import Task
from edison.core.qa.models import QARecord
from edison.core.config import WorkflowConfig
from edison.core.exceptions import TaskStateError

@pytest.fixture
def repo_env(tmp_path, monkeypatch):
    """Setup a repository environment with configuration."""
    repo = tmp_path
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"

    # 1. defaults.yaml (State Machine)
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
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

    # 3. workflow.yaml
    write_yaml(
        config_dir / "workflow.yaml",
        {
            "version": "1.0",
            "validationLifecycle": {
                "onApprove": {
                    "taskState": "done → validated",
                    "qaState": "done → validated"
                },
            }
        }
    )

    # 4. record_metadata.yaml (for TYPE_INFO defaults)
    write_yaml(
        config_dir / "record_metadata.yaml",
        {
            "task": {
                "default_status": "todo"
            },
            "qa": {
                "default_status": "waiting"
            }
        }
    )

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    # Clear config caches
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Reload config-dependent modules
    import edison.core.config.domains.task as task_config
    importlib.reload(task_config)
    import edison.core.task.paths as paths
    importlib.reload(paths)

    return repo

# ========== TDD Tests: create_task() ==========

def test_create_task_basic(repo_env):
    """TaskQAWorkflow.create_task() creates task in todo state."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    task = workflow.create_task(task_id="T-001", title="Test Task")

    # Assert - task created
    assert task is not None
    assert task.id == "T-001"
    assert task.title == "Test Task"
    assert task.state == "todo"
    assert task.description == ""
    assert task.session_id is None

    # Assert - file exists in correct location
    task_path = repo_env / ".project" / "tasks" / "todo" / "T-001.md"
    assert task_path.exists()

def test_create_task_with_description(repo_env):
    """TaskQAWorkflow.create_task() saves description."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    task = workflow.create_task(
        task_id="T-002",
        title="Task with description",
        description="This is a detailed description"
    )

    # Assert
    assert task.description == "This is a detailed description"

    # Verify file content includes description
    task_path = repo_env / ".project" / "tasks" / "todo" / "T-002.md"
    content = task_path.read_text()
    assert "This is a detailed description" in content

def test_create_task_creates_qa_record(repo_env):
    """TaskQAWorkflow.create_task() creates associated QA record."""
    workflow = TaskQAWorkflow(project_root=repo_env)
    qa_repo = QARepository(project_root=repo_env)

    # Act
    task = workflow.create_task(task_id="T-003", title="Task with QA")

    # Assert - QA created
    qa_id = f"{task.id}-qa"
    qa = qa_repo.get(qa_id)
    assert qa is not None
    assert qa.id == qa_id
    assert qa.task_id == task.id
    assert qa.state == "waiting"  # default QA state

    # Assert - QA file exists
    qa_path = repo_env / ".project" / "qa" / "waiting" / f"{qa_id}.md"
    assert qa_path.exists()

def test_create_task_with_session_id(repo_env):
    """TaskQAWorkflow.create_task() can create task in session."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    task = workflow.create_task(
        task_id="T-004",
        title="Session Task",
        session_id="sess-1"
    )

    # Assert
    assert task.session_id == "sess-1"

    # File created in session directory (session tasks still start in todo but within session)
    # Based on existing patterns, tasks with session_id go to session location
    task_path = repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "todo" / "T-004.md"
    assert task_path.exists()

def test_create_task_with_owner(repo_env):
    """TaskQAWorkflow.create_task() records owner in metadata."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    task = workflow.create_task(
        task_id="T-005",
        title="Owned Task",
        owner="alice"
    )

    # Assert
    assert task.metadata.created_by == "alice"

def test_create_task_duplicate_raises_error(repo_env):
    """TaskQAWorkflow.create_task() raises error if task exists."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    # Create first task
    workflow.create_task(task_id="T-006", title="First")

    # Try to create duplicate
    with pytest.raises(TaskStateError, match="already exists"):
        workflow.create_task(task_id="T-006", title="Duplicate")

def test_create_task_returns_persisted_task(repo_env):
    """TaskQAWorkflow.create_task() returns task that can be retrieved."""
    workflow = TaskQAWorkflow(project_root=repo_env)
    repo = TaskRepository(project_root=repo_env)

    # Act
    created_task = workflow.create_task(task_id="T-007", title="Retrievable")

    # Should be able to get it back via repository
    retrieved_task = repo.get("T-007")
    assert retrieved_task is not None
    assert retrieved_task.id == created_task.id
    assert retrieved_task.title == created_task.title

def test_create_task_qa_inherits_session_id(repo_env):
    """TaskQAWorkflow.create_task() creates QA with same session_id."""
    workflow = TaskQAWorkflow(project_root=repo_env)
    qa_repo = QARepository(project_root=repo_env)

    # Act
    task = workflow.create_task(
        task_id="T-008",
        title="Task with Session QA",
        session_id="sess-2"
    )

    # Assert - QA has session_id
    qa = qa_repo.get(f"{task.id}-qa")
    assert qa is not None
    assert qa.session_id == "sess-2"

def test_create_task_sets_timestamps(repo_env):
    """TaskQAWorkflow.create_task() sets created_at and updated_at."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    task = workflow.create_task(task_id="T-009", title="Timestamped")

    # Assert
    assert task.metadata.created_at is not None
    assert task.metadata.updated_at is not None
    # Initially they should be the same
    assert task.metadata.created_at == task.metadata.updated_at

def test_create_task_without_qa_option(repo_env):
    """TaskQAWorkflow.create_task() can skip QA creation if requested."""
    workflow = TaskQAWorkflow(project_root=repo_env)
    qa_repo = QARepository(project_root=repo_env)

    # Act - create task without QA
    task = workflow.create_task(
        task_id="T-010",
        title="No QA Task",
        create_qa=False
    )

    # Assert - task exists
    assert task is not None

    # Assert - QA does NOT exist
    qa = qa_repo.get(f"{task.id}-qa")
    assert qa is None

def test_create_task_qa_title_includes_task_title(repo_env):
    """TaskQAWorkflow.create_task() creates QA with informative title."""
    workflow = TaskQAWorkflow(project_root=repo_env)
    qa_repo = QARepository(project_root=repo_env)

    # Act
    task = workflow.create_task(task_id="T-011", title="Feature X")

    # Assert - QA title references task
    qa = qa_repo.get(f"{task.id}-qa")
    assert qa is not None
    # QA title should include task info
    assert "T-011" in qa.title or "Feature X" in qa.title
