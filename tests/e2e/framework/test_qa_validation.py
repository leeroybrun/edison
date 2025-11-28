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
from edison.core.task import TaskRepository, TaskQAWorkflow
from edison.core.qa.repository import QARepository


def test_qa_checklist_and_validation_workflow(tmp_path):
    """Ensures QA brief pairing and state transitions across the QA pipeline."""
    sid = 'sess-qa-1'
    ensure_session(sid)
    task_id = 'T3001'

    # Clean up any existing task from previous runs
    task_repo = TaskRepository()
    qa_repo = QARepository()
    workflow = TaskQAWorkflow()
    if task_repo.exists(task_id):
        task_repo.delete(task_id)
    qa_id = f'{task_id}-qa'
    if qa_repo.exists(qa_id):
        qa_repo.delete(qa_id)

    # Create task using TaskQAWorkflow
    task = workflow.create_task(task_id, title='Feature Y', create_qa=True)

    # Claim then complete the task → QA goes waiting -> todo
    workflow.claim_task(task_id, sid)
    workflow.complete_task(task_id, sid)

    # Progress QA: todo -> wip -> done -> validated
    # Use repository to verify QA state transitions
    qa_repo = QARepository()
    qa_id = f'{task_id}-qa'

    # Verify QA is in todo state after task completion
    qa = qa_repo.get(qa_id)
    assert qa is not None
    assert qa.state == 'todo'

    # Advance to wip
    qa_repo.advance_state(qa_id, 'wip', session_id=sid)
    qa = qa_repo.get(qa_id)
    assert qa is not None
    assert qa.state == 'wip'

    # Advance to done
    qa_repo.advance_state(qa_id, 'done', session_id=sid)
    qa = qa_repo.get(qa_id)
    assert qa is not None
    assert qa.state == 'done'

    # Advance to validated
    qa_repo.advance_state(qa_id, 'validated', session_id=sid)
    qa = qa_repo.get(qa_id)
    assert qa is not None
    assert qa.state == 'validated'
