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
from edison.core.sessionlib import ensure_session 
from edison.core.task import create_task, ready_task, qa_progress 
def test_qa_checklist_and_validation_workflow(tmp_path):
    """Ensures QA brief pairing and state transitions across the QA pipeline."""
    sid = 'sess-qa-1'
    ensure_session(sid)
    task_id = 'T3001'
    create_task(task_id, title='Feature Y')
    # Claim then ready the task → QA goes waiting -> todo
    from edison.core.task import claim_task  # local import to avoid unused in file
    claim_task(task_id, sid)
    ready_task(task_id, sid)
    # QA files are session-scoped, organized within the session's state directory
    # Session is in "wip" state, QA files are in .../wip/sess-qa-1/qa/<qa_state>/
    qa_todo = Path('.project/sessions/wip') / sid / 'qa' / 'todo' / f'{task_id}-qa.md'
    assert qa_todo.exists()

    # Progress QA: todo -> wip -> done -> validated (session-scoped)
    qa_progress(task_id, 'todo', 'wip', session_id=sid)
    qa_wip = Path('.project/sessions/wip') / sid / 'qa' / 'wip' / f'{task_id}-qa.md'
    assert qa_wip.exists()

    qa_progress(task_id, 'wip', 'done', session_id=sid)
    qa_done = Path('.project/sessions/wip') / sid / 'qa' / 'done' / f'{task_id}-qa.md'
    assert qa_done.exists()

    qa_progress(task_id, 'done', 'validated', session_id=sid)
    qa_val = Path('.project/sessions/wip') / sid / 'qa' / 'validated' / f'{task_id}-qa.md'
    assert qa_val.exists()
