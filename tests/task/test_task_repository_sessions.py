"""Tests for session-aware TaskRepository lookups.

These tests ensure that TaskRepository correctly identifies and retrieves
tasks stored in session-specific directories.
"""
from __future__ import annotations
from helpers.io_utils import write_yaml

from pathlib import Path
import importlib
import pytest

from edison.core.task.repository import TaskRepository
from edison.core.entity import EntityMetadata

def _bootstrap_repo(repo: Path) -> None:
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                        "done": {"allowed_transitions": []},
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
    """Setup a repository environment with session directories."""
    repo = tmp_path
    _bootstrap_repo(repo)

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

def create_markdown_task(path: Path, task_id: str, title: str, session_id: str = None):
    """Helper to create a raw markdown task file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    content = [
        f"<!-- Status: {path.parent.name} -->"
    ]
    if session_id:
        content.append(f"<!-- Session: {session_id} -->")
    
    content.extend([
        "",
        f"# {title}",
        "",
        "Description here."
    ])
    
    path.write_text("\n".join(content), encoding="utf-8")

def test_get_task_from_session_directory(repo_env):
    """Test that TaskRepository.get() finds tasks in session directories."""
    session_id = "sess-001"
    task_id = "T-SESS-1"
    
    # Create session task in .project/sessions/wip/{session_id}/tasks/todo/
    session_task_path = (
        repo_env / ".project" / "sessions" / "wip" / session_id / "tasks" / "todo" / f"{task_id}.md"
    )
    create_markdown_task(session_task_path, task_id, "Session Task", session_id)
    
    repo = TaskRepository(project_root=repo_env)
    
    # This should fail currently as TaskRepository doesn't look in sessions
    task = repo.get(task_id)
    
    assert task is not None
    assert task.id == task_id
    assert task.session_id == session_id
    assert task.title == "Session Task"

def test_list_all_includes_session_tasks(repo_env):
    """Test that TaskRepository.list_all() includes tasks from global and session dirs."""
    # 1. Create global task
    global_task_path = repo_env / ".project" / "tasks" / "todo" / "T-GLOBAL-1.md"
    create_markdown_task(global_task_path, "T-GLOBAL-1", "Global Task")
    
    # 2. Create session 1 task
    sess1_path = repo_env / ".project" / "sessions" / "wip" / "sess-1" / "tasks" / "wip" / "T-SESS-1.md"
    create_markdown_task(sess1_path, "T-SESS-1", "Session 1 Task", "sess-1")
    
    # 3. Create session 2 task
    sess2_path = repo_env / ".project" / "sessions" / "wip" / "sess-2" / "tasks" / "todo" / "T-SESS-2.md"
    create_markdown_task(sess2_path, "T-SESS-2", "Session 2 Task", "sess-2")
    
    repo = TaskRepository(project_root=repo_env)
    
    # This should fail as it will only find the global task
    tasks = repo.list_all()
    
    task_ids = {t.id for t in tasks}
    assert "T-GLOBAL-1" in task_ids
    assert "T-SESS-1" in task_ids
    assert "T-SESS-2" in task_ids
    assert len(tasks) == 3

def test_find_by_session_filters_correctly(repo_env):
    """Test that finding by session ID works correctly across directories."""
    # Global task with NO session
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-G1.md",
        "T-G1", "Global No Session"
    )
    
    # Global task WITH session (simulating migrated/moved task)
    create_markdown_task(
        repo_env / ".project" / "tasks" / "todo" / "T-G2.md",
        "T-G2", "Global With Session", session_id="target-sess"
    )
    
    # Target Session task
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "target-sess" / "tasks" / "todo" / "T-S1.md",
        "T-S1", "Session Task", session_id="target-sess"
    )
    
    # Other Session task
    create_markdown_task(
        repo_env / ".project" / "sessions" / "wip" / "other-sess" / "tasks" / "todo" / "T-S2.md",
        "T-S2", "Other Session Task", session_id="other-sess"
    )
    
    repo = TaskRepository(project_root=repo_env)
    
    # Should find both the global one with metadata and the one in session dir
    tasks = repo.find(session_id="target-sess")
    
    found_ids = {t.id for t in tasks}
    assert "T-S1" in found_ids
    assert "T-G2" in found_ids
    assert "T-G1" not in found_ids
    assert "T-S2" not in found_ids
    assert len(tasks) == 2
