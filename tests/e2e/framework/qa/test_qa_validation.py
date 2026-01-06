import sys
import os
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
from edison.core.qa.workflow.repository import QARepository
from edison.core.qa.evidence.service import EvidenceService
from edison.core.qa.evidence.command_evidence import write_command_evidence
from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir
from edison.core.utils.git.fingerprint import compute_repo_fingerprint
from edison.core.registries.validators import ValidatorRegistry
from edison.core.config.domains.qa import QAConfig


def test_qa_checklist_and_validation_workflow(tmp_path, monkeypatch):
    """Ensures QA brief pairing and state transitions across the QA pipeline."""
    # Isolate this workflow to a temp project root so it doesn't depend on
    # (or mutate) the developer's local `.project` state.
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)

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

    # Completion is guarded by implementation-report evidence; seed minimal evidence for the test.
    ev = EvidenceService(task_id, project_root=tmp_path)
    ev.ensure_round(1)
    ev.write_implementation_report({"summary": "E2E test implementation report"}, round_num=1)
    ev.write_bundle({"approved": True, "summary": "E2E bundle approval"}, round_num=1)

    # Command evidence is repo-state; write it into the snapshot store.
    snap_key = current_snapshot_key(project_root=tmp_path)
    snap = snapshot_dir(project_root=tmp_path, key=snap_key)
    fp = compute_repo_fingerprint(tmp_path)
    for marker in (
        "command-type-check.txt",
        "command-lint.txt",
        "command-test.txt",
        "command-build.txt",
    ):
        write_command_evidence(
            path=snap / marker,
            task_id=task_id,
            round_num=0,
            command_name=marker.replace("command-", "").replace(".txt", ""),
            command="echo ok",
            cwd=str(tmp_path),
            exit_code=0,
            output="ok\n",
            fingerprint=fp,
        )

    # Seed minimal validator reports so QA can advance through done/validated in this test.
    qa_cfg = QAConfig(repo_root=tmp_path)
    registry = ValidatorRegistry(project_root=qa_cfg.repo_root)
    roster = registry.build_execution_roster(task_id=task_id, session_id=sid, wave=None, extra_validators=None)
    candidates = (roster.get("alwaysRequired") or []) + (roster.get("triggeredBlocking") or []) + (roster.get("triggeredOptional") or [])
    for v in candidates:
        if not isinstance(v, dict) or not v.get("blocking"):
            continue
        vid = str(v.get("id") or "").strip()
        if not vid:
            continue
        ev.write_validator_report(vid, {"validatorId": vid, "verdict": "approve"}, round_num=1)

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
