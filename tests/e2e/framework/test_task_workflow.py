import sys
from pathlib import Path

# Add Edison core to path
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = _THIS_FILE.parents[4]

CORE_ROOT = _CORE_ROOT
from tests.helpers.session import ensure_session 
from edison.core.task import create_task, claim_task, ready_task 
def test_task_claim_work_complete_flow(tmp_path):
    """Runs Claim → Work → Complete flow and verifies file locations."""
    sid = 'sess-taskflow-1'
    ensure_session(sid)
    task_id = 'T2001'
    todo = create_task(task_id, title='Implement X')
    _, wip = claim_task(task_id, sid)
    assert not todo.exists()
    assert wip.exists()
    _, done = ready_task(task_id, sid)
    assert not wip.exists()
    assert done.exists()
