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
if str(CORE_ROOT) not in sys.path:

from edison.core.task import create_task 
def test_task_file_initialization(tmp_path):
    """Creates a task file in `.project/tasks/todo/` with YAML frontmatter."""
    task_id = 'T1001'
    path = create_task(task_id, title='Demo', description='desc')
    assert path.exists()
    content = path.read_text(encoding='utf-8')
    assert 'status: todo' in content
    assert f'id: {task_id}' in content
