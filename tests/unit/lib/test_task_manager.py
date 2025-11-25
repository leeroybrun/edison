from __future__ import annotations

from pathlib import Path
import importlib

import pytest

from edison.core.paths import PathResolver 
def _write_state_machine_config(root: Path) -> None:
    """Provide a minimal state-machine config in the modular layout."""
    cfg_dir = root / ".agents" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "state-machine.yml").write_text(
        "\n".join(
            [
                "statemachine:",
                "  task:",
                "    states:",
                "      todo:",
                "        transitions: [wip]",
                "      wip:",
                "        transitions: [blocked, done]",
                "      blocked:",
                "        transitions: [wip]",
                "      done:",
                "        transitions: [validated]",
                "      validated:",
                "        transitions: []",
                "  qa:",
                "    states:",
                "      waiting:",
                "        transitions: [todo]",
                "      todo:",
                "        transitions: [wip]",
                "      wip:",
                "        transitions: [done]",
                "      done:",
                "        transitions: [validated]",
                "      validated:",
                "        transitions: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _fresh_task_modules():
    """Reload task modules so path constants follow the per-test project root."""
    importlib.invalidate_caches()
    paths_mod = importlib.reload(importlib.import_module("edison.core.task.paths"))  # type: ignore
    store_mod = importlib.reload(importlib.import_module("edison.core.task.store"))  # type: ignore
    locking_mod = importlib.reload(importlib.import_module("edison.core.task.locking"))  # type: ignore
    metadata_mod = importlib.reload(importlib.import_module("edison.core.task.metadata"))  # type: ignore
    finder_mod = importlib.reload(importlib.import_module("edison.core.task.finder"))  # type: ignore
    io_mod = importlib.reload(importlib.import_module("edison.core.task.io"))  # type: ignore
    task_mod = importlib.reload(importlib.import_module("edison.core.task"))  # type: ignore
    manager_mod = importlib.reload(importlib.import_module("edison.core.tasks.manager"))  # type: ignore
    state_mod = importlib.reload(importlib.import_module("edison.core.tasks.state"))  # type: ignore
    return manager_mod.TaskManager, state_mod


def _task_path(root: Path, task_id: str, *, status: str = "todo") -> Path:
    project_root = PathResolver.resolve_project_root()
    assert project_root == root
    filename = f"task-{task_id}.md"
    return project_root / ".project" / "tasks" / status / filename


def _session_task_path(root: Path, session_id: str, task_id: str, *, status: str = "wip") -> Path:
    project_root = PathResolver.resolve_project_root()
    assert project_root == root
    filename = f"task-{task_id}.md"
    return (
        project_root
        / ".project"
        / "sessions"
        / "wip"
        / session_id
        / "tasks"
        / status
        / filename
    )


@pytest.mark.task
def test_claim_task_moves_from_todo_to_session_wip(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    TaskManager.claim_task should move a task card from the global
    `tasks/todo` queue into the session-scoped `sessions/wip/<sid>/tasks/wip`
    directory and update its status in-place.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    root = PathResolver.resolve_project_root()
    assert root == isolated_project_env

    task_id = "123-task-manager"
    todo_path = _task_path(root, task_id, status="todo")
    todo_path.parent.mkdir(parents=True, exist_ok=True)
    todo_path.write_text("---\nstatus: todo\n---\n", encoding="utf-8")

    _write_state_machine_config(root)
    TaskManager, _ = _fresh_task_modules()
    from edison.core.task import paths as task_paths 
    assert task_paths.ROOT.resolve() == root.resolve()
    mgr = TaskManager()
    session_id = "sess-for-task-claim"

    dest = mgr.claim_task(task_id, session_id)
    assert dest.exists()
    assert not todo_path.exists()

    # Verify destination lives under the session-scoped wip tree
    expected = _session_task_path(root, session_id, task_id, status="wip")
    assert dest.resolve() == expected.resolve()
    content = dest.read_text(encoding="utf-8")
    assert "status: wip" in content


@pytest.mark.task
def test_transition_task_updates_status_and_directory(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    TaskManager.transition_task should move a session-scoped task between
    status directories and keep the Status line in sync.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    root = PathResolver.resolve_project_root()
    assert root == isolated_project_env

    task_id = "456-task-transition"
    todo_path = _task_path(root, task_id, status="todo")
    todo_path.parent.mkdir(parents=True, exist_ok=True)
    todo_path.write_text("---\nstatus: todo\n---\n", encoding="utf-8")

    _write_state_machine_config(root)
    TaskManager, _ = _fresh_task_modules()
    from edison.core.task import paths as task_paths 
    assert task_paths.ROOT.resolve() == root.resolve()
    mgr = TaskManager()
    session_id = "sess-for-task-transition"

    # Start in wip under the session
    mgr.claim_task(task_id, session_id)
    wip_path = _session_task_path(root, session_id, task_id, status="wip")
    assert wip_path.exists()

    # Move to blocked
    blocked_path = mgr.transition_task(task_id, "blocked", session_id=session_id)
    assert blocked_path.exists()
    assert not wip_path.exists()
    content = blocked_path.read_text(encoding="utf-8")
    assert "status: blocked" in content


@pytest.mark.task
def test_task_state_machine_rejects_invalid_transition() -> None:
    """
    TaskStateMachine must fail-closed for invalid transitions according
    to the defaults.yaml state machine.
    """
    _, task_state = _fresh_task_modules()
    machine = task_state.build_default_state_machine()
    # todo → validated is not allowed directly
    with pytest.raises(Exception):
        machine.validate("todo", "validated")


@pytest.mark.task
def test_transition_task_invalid_status_raises(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    TaskManager.transition_task should surface a ValueError when asked to
    move to an unknown status.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    root = PathResolver.resolve_project_root()
    assert root == isolated_project_env

    task_id = "789-task-invalid-status"
    todo_path = _task_path(root, task_id, status="todo")
    todo_path.parent.mkdir(parents=True, exist_ok=True)
    todo_path.write_text("---\nstatus: todo\n---\n", encoding="utf-8")

    _write_state_machine_config(root)
    TaskManager, _ = _fresh_task_modules()
    from edison.core.task import paths as task_paths 
    assert task_paths.ROOT.resolve() == root.resolve()
    mgr = TaskManager()
    session_id = "sess-for-invalid-status"
    mgr.claim_task(task_id, session_id)

    with pytest.raises(ValueError):
        mgr.transition_task(task_id, "not-a-status", session_id=session_id)
