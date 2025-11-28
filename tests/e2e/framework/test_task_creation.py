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

from edison.core.task import TaskRepository, TaskQAWorkflow


def test_task_file_initialization(tmp_path):
    """Creates a task file in `.project/tasks/todo/` with markdown format."""
    task_id = 'T1001'
    task_repo = TaskRepository()
    workflow = TaskQAWorkflow()

    # Clean up any existing task from previous runs
    if task_repo.exists(task_id):
        task_repo.delete(task_id)

    # Create task using TaskQAWorkflow
    task = workflow.create_task(task_id, title='Demo', description='desc', create_qa=False)

    # Verify task file exists
    task_file = task_repo._find_entity_path(task_id)
    assert task_file is not None
    assert task_file.exists()

    # Verify content (new format uses markdown with HTML comments)
    content = task_file.read_text(encoding='utf-8')
    assert 'Status: todo' in content
    assert '# Demo' in content
    assert 'desc' in content
