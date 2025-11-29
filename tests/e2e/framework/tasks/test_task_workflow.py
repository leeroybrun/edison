import sys
from pathlib import Path

from tests.helpers.paths import get_repo_root

# Add Edison core to path
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

from tests.helpers.session import ensure_session
from edison.core.task import TaskRepository, TaskQAWorkflow


def test_task_claim_work_complete_flow(tmp_path):
    """Runs Claim → Work → Complete flow and verifies file locations."""
    sid = 'sess-taskflow-1'
    ensure_session(sid)
    task_id = 'T2001'

    task_repo = TaskRepository()
    workflow = TaskQAWorkflow()

    # Clean up any existing task from previous runs
    if task_repo.exists(task_id):
        task_repo.delete(task_id)

    # Create task (in global todo)
    task = workflow.create_task(task_id, title='Implement X', create_qa=False)
    todo_path = task_repo._find_entity_path(task_id)
    assert todo_path is not None
    assert todo_path.exists()

    # Claim task (moves to session wip)
    workflow.claim_task(task_id, sid)
    wip_path = task_repo._find_entity_path(task_id)
    assert wip_path is not None
    assert wip_path.exists()
    assert 'wip' in str(wip_path)
    assert sid in str(wip_path)
    # Original todo should be gone
    assert not todo_path.exists()

    # Complete task (moves to session done)
    workflow.complete_task(task_id, sid)
    done_path = task_repo._find_entity_path(task_id)
    assert done_path is not None
    assert done_path.exists()
    assert 'done' in str(done_path)
    assert sid in str(done_path)
    # wip should be gone
    assert not wip_path.exists()
