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

from edison.core.task import TaskRepository, TaskQAWorkflow
from edison.core.utils.text import parse_frontmatter


def test_task_file_initialization(tmp_path, monkeypatch):
    """Creates a task file in `.project/tasks/todo/` with markdown format."""
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)
    task_id = 'T1001'
    task_repo = TaskRepository(project_root=tmp_path)
    workflow = TaskQAWorkflow(project_root=tmp_path)

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
    assert task_file.parent.name == "todo"
    fm = parse_frontmatter(content).frontmatter
    assert fm.get("id") == task_id
    assert fm.get("title") == "Demo"
    assert '# Demo' in content
    assert 'desc' in content
