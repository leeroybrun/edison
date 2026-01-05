"""Test task delegation functionality using Repository-based API.

Tests cover:
- Child task result tracking and aggregation
- Agent tracking in delegation
- Parent-child task linking
- Configuration validation CLI (delegation-related)
"""
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any

from tests.helpers.paths import get_repo_root

# Add Edison core to path (so `import edison.core.*` works like other tests)
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = get_repo_root()

CORE_ROOT = _CORE_ROOT
import pytest

# Import modules and classes
from edison.core.task import TaskRepository, Task
from tests.helpers import delegation as _delegationlib  # type: ignore
from tests.helpers.session import ensure_session
from edison.core.utils.subprocess import run_with_timeout
from edison.core.task import TaskQAWorkflow


# Helper functions to replace legacy compat API
def create_task_record(title: str, session_id: str, parent_task_id: str = None) -> str:
    """Create a task record via the canonical workflow layer (registers session links)."""
    workflow = TaskQAWorkflow()
    task = workflow.create_task(
        task_id=f"task-{os.urandom(4).hex()}",
        title=title,
        description="",
        session_id=session_id,
        parent_id=parent_task_id,
        create_qa=False,
    )
    return task.id


def load_task_record(task_id: str) -> Dict[str, Any]:
    """Load a task record using TaskRepository."""
    repo = TaskRepository()
    task = repo.get(task_id)
    if task is None:
        raise FileNotFoundError(f"Task record not found: {task_id}")
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.state,
        "session_id": task.session_id,
        "parent_task_id": task.parent_id,
        "child_tasks": list(task.child_ids or []),
        "agent": task.delegated_to,
    }


def set_task_result(task_id: str, status: str = None, result: Any = None, error: str = None) -> Dict[str, Any]:
    """Set task result using TaskRepository."""
    repo = TaskRepository()
    task = repo.get(task_id)
    if task is None:
        raise FileNotFoundError(f"Task record not found: {task_id}")

    if status:
        # Test-friendly status surface (success/failure) maps to real Edison task states.
        s = str(status).lower()
        if s in ("success", "ok", "completed"):
            task.state = "done"
        elif s in ("failure", "failed", "error"):
            task.state = "done"
        elif s in ("in_progress", "wip", "running"):
            task.state = "wip"
        else:
            task.state = "todo"
    if result is not None:
        task.result = str(result)
    if error is not None:
        task.result = f"Error: {error}"
    if (task.state == "done") and (task.result is None):
        if status and str(status).lower() in ("failure", "failed", "error"):
            task.result = "Error: failure"
        else:
            # Avoid treating a done task with no result as a failure by default.
            task.result = "ok"

    repo.save(task)

    return {
        "id": task.id,
        "status": task.state,
        "result": task.result,
    }


def test_child_task_result_tracking(tmp_path, isolated_project_env):
    """D5: Child task result tracking and aggregation surface exists and works minimally.

    RED phase: we expect this to fail until implementations are added in task/delegationlib.
    """
    # Check that delegation helper exists
    assert hasattr(_delegationlib, 'delegate_task'), "delegate_task function must exist"
    assert hasattr(_delegationlib, 'aggregate_child_results'), "aggregate_child_results function must exist"

    # Minimal happy path scenario (will execute once GREEN is implemented)
    sid = 'sess-g4-d5-1'
    ensure_session(sid)

    parent_id = create_task_record("Parent task for D5", session_id=sid)
    child_ok = _delegationlib.delegate_task("Child OK", agent='codex', parent_task_id=parent_id, session_id=sid)
    child_fail = _delegationlib.delegate_task("Child FAIL", agent='claude', parent_task_id=parent_id, session_id=sid)

    set_task_result(child_ok, status='success', result={"message": "done"})
    set_task_result(child_fail, status='failure', error='boom')

    parent = load_task_record(parent_id)
    assert 'child_tasks' in parent and set(parent['child_tasks']) >= {child_ok, child_fail}

    agg = _delegationlib.aggregate_child_results(parent_id)
    assert agg['total'] == 2
    assert agg['counts']['success'] == 1
    assert agg['counts']['failure'] == 1
    assert agg['status'] == 'partial_failure'


def test_delegation_tracks_agent(tmp_path, isolated_project_env):
    """D5: Delegation records which agent executed each child task."""
    assert hasattr(_delegationlib, 'delegate_task'), "delegate_task function must exist"

    sid = 'sess-g4-d5-2'
    ensure_session(sid)
    parent_id = create_task_record("Parent for agent tracking", session_id=sid)
    child = _delegationlib.delegate_task("Child A", agent='codex', parent_task_id=parent_id, session_id=sid)

    child_rec = load_task_record(child)
    assert child_rec.get('agent') == 'codex'


def test_aggregate_child_results(tmp_path, isolated_project_env):
    """D5: Aggregation returns counts and overall status from real child results."""
    assert hasattr(_delegationlib, 'delegate_task'), "delegate_task function must exist"
    assert hasattr(_delegationlib, 'aggregate_child_results'), "aggregate_child_results function must exist"

    sid = 'sess-g4-d5-3'
    ensure_session(sid)
    parent_id = create_task_record("Parent for aggregation", session_id=sid)

    c1 = _delegationlib.delegate_task("C1", agent='codex', parent_task_id=parent_id, session_id=sid)
    c2 = _delegationlib.delegate_task("C2", agent='claude', parent_task_id=parent_id, session_id=sid)
    c3 = _delegationlib.delegate_task("C3", agent='gemini', parent_task_id=parent_id, session_id=sid)

    set_task_result(c1, status='success')
    set_task_result(c2, status='failure')
    set_task_result(c3, status='success')

    agg = _delegationlib.aggregate_child_results(parent_id)
    assert agg['total'] == 3
    assert agg['counts'] == {'success': 2, 'failure': 1, 'pending': 0}
    assert agg['status'] == 'partial_failure'


def test_delegation_validation_cli_missing_or_fails(tmp_path, isolated_project_env):
    """D6: Delegation config validation fails for invalid project overrides.

    Edison centralizes validation under `edison config validate`.
    """
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".edison" / "config" / "delegation.yaml").write_text(
        "delegation: 123\n",
        encoding="utf-8",
    )

    proc = run_with_timeout(
        [sys.executable, "-m", "edison", "config", "validate", "--repo-root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "schema" in (proc.stderr or proc.stdout).lower()


def test_delegation_validation_cli_passes_with_valid_config(tmp_path, isolated_project_env):
    """D6: Validator succeeds on a well-formed delegation override."""
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".edison" / "config" / "delegation.yaml").write_text(
        "\n".join(
            [
                "delegation:",
                "  implementers:",
                "    primary: codex",
                "    fallbackChain: [gemini, claude]",
                "    maxFallbackAttempts: 3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    proc = run_with_timeout(
        [sys.executable, "-m", "edison", "config", "validate", "--repo-root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Expected validator to pass, got stderr: {proc.stderr} stdout: {proc.stdout}"


def test_task_session_linking(tmp_path, isolated_project_env):
    """S1: Task records link to session (task side) and session lists task.

    Validates bidirectional linkage from the task perspective.
    """
    sid = 'sess-g4-s1-1'
    ensure_session(sid)
    tid = create_task_record("Linked task", session_id=sid)
    task = load_task_record(tid)
    assert task.get('session_id') == sid

    # Session JSON is not a task index; directory structure is the source of truth.
    repo = TaskRepository()
    task_path = repo.get_path(tid)
    assert sid in str(task_path), f"Expected session-scoped task path, got: {task_path}"


def test_delegate_task_updates_parent_child_tasks_list(isolated_project_env):
    """TDD: delegate_task() must update parent's child_tasks list when creating a child.

    This is the core parent-child linking test that must pass.
    RED phase: This will fail until delegation.py properly updates the parent record.
    """
    assert hasattr(_delegationlib, 'delegate_task'), "delegate_task function must exist"

    sid = 'sess-parent-child-link-1'
    ensure_session(sid)

    # Create parent task
    parent_id = f"parent-task-{os.urandom(4).hex()}"
    parent_task = TaskQAWorkflow().create_task(
        parent_id,
        title="Parent Task",
        description="",
        session_id=sid,
        create_qa=False,
    )

    # Delegate a child task
    child_id = _delegationlib.delegate_task(
        description="Child task description",
        agent='codex',
        parent_task_id=parent_id,
        session_id=sid
    )

    # Load parent and verify child is in its child_tasks list
    parent = load_task_record(parent_id)
    assert 'child_tasks' in parent, "Parent task must have child_tasks field"
    assert isinstance(parent['child_tasks'], list), "child_tasks must be a list"
    assert child_id in parent['child_tasks'], f"Child {child_id} must be in parent's child_tasks list"

    # Delegate a second child to ensure it appends properly
    child_id_2 = _delegationlib.delegate_task(
        description="Second child task",
        agent='claude',
        parent_task_id=parent_id,
        session_id=sid
    )

    # Reload parent and verify both children are tracked
    parent = load_task_record(parent_id)
    assert len(parent['child_tasks']) == 2, "Parent should track both children"
    assert child_id in parent['child_tasks'], "First child must still be in list"
    assert child_id_2 in parent['child_tasks'], "Second child must be in list"
