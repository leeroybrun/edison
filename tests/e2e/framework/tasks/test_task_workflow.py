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


def test_task_claim_work_complete_flow(tmp_path, isolated_project_env):
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

    # Create required implementation evidence before finishing.
    from edison.core.qa.evidence import tracking
    tracking.start_implementation(task_id, project_root=isolated_project_env, round_num=1, model="test")

    # Satisfy evidence requirements enforced by task completion guards.
    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.qa.evidence.service import EvidenceService
    from edison.core.qa.policy.resolver import ValidationPolicyResolver

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    round_dir = ev.get_round_dir(1)
    policy = ValidationPolicyResolver(project_root=isolated_project_env).resolve_for_task(task_id, session_id=sid)
    for pattern in policy.required_evidence or []:
        name = str(pattern).strip()
        if not name.startswith("command-") or not name.endswith(".txt"):
            continue
        path = round_dir / name
        if path.exists():
            continue
        write_command_evidence(
            path=path,
            task_id=task_id,
            round_num=1,
            command_name=name.removeprefix("command-").removesuffix(".txt"),
            command="echo ok",
            cwd=str(isolated_project_env),
            exit_code=0,
            output="ok\n",
            runner="edison-tests",
        )

    # Complete task (moves to session done)
    workflow.complete_task(task_id, sid)
    done_path = task_repo._find_entity_path(task_id)
    assert done_path is not None
    assert done_path.exists()
    assert 'done' in str(done_path)
    assert sid in str(done_path)
    # wip should be gone
    assert not wip_path.exists()
