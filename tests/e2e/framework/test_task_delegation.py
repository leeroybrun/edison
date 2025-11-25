import sys
import os
import json
import subprocess
from pathlib import Path

# Add Edison core to path (so `import edison.core.*` works like other tests)
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

import pytest

# Import modules (not specific symbols) so missing functions cause clear RED failures per-test
from edison.core import task as _task  # type: ignore
from edison.core import delegationlib as _delegationlib  # type: ignore
from edison.core.sessionlib import ensure_session 
from edison.core.utils.subprocess import run_with_timeout


def _require_attr(module, name: str):
    """Assert a module exposes an attribute (function) required by Group 4.

    Produces a crisp RED failure explaining what is missing before GREEN work.
    """
    assert hasattr(module, name), f"Missing required function `{name}` in {module.__name__} (Group 4 spec)"


def test_child_task_result_tracking(tmp_path):
    """D5: Child task result tracking and aggregation surface exists and works minimally.

    RED phase: we expect this to fail until implementations are added in task/delegationlib.
    """
    # API surface checks (fail fast with clear messages if missing)
    _require_attr(_task, 'create_task_record')
    _require_attr(_task, 'load_task_record')
    _require_attr(_task, 'set_task_result')
    _require_attr(_delegationlib, 'delegate_task')
    _require_attr(_delegationlib, 'aggregate_child_results')

    # Minimal happy path scenario (will execute once GREEN is implemented)
    sid = 'sess-g4-d5-1'
    ensure_session(sid)

    parent_id = _task.create_task_record("Parent task for D5", session_id=sid)
    child_ok = _delegationlib.delegate_task("Child OK", agent='codex', parent_task_id=parent_id, session_id=sid)
    child_fail = _delegationlib.delegate_task("Child FAIL", agent='claude', parent_task_id=parent_id, session_id=sid)

    _task.set_task_result(child_ok, status='success', result={"message": "done"})
    _task.set_task_result(child_fail, status='failure', error='boom')

    parent = _task.load_task_record(parent_id)
    assert 'child_tasks' in parent and set(parent['child_tasks']) >= {child_ok, child_fail}

    agg = _delegationlib.aggregate_child_results(parent_id)
    assert agg['total'] == 2
    assert agg['counts']['success'] == 1
    assert agg['counts']['failure'] == 1
    assert agg['status'] == 'partial_failure'


def test_delegation_tracks_agent(tmp_path):
    """D5: Delegation records which agent executed each child task."""
    _require_attr(_task, 'create_task_record')
    _require_attr(_task, 'load_task_record')
    _require_attr(_delegationlib, 'delegate_task')

    sid = 'sess-g4-d5-2'
    ensure_session(sid)
    parent_id = _task.create_task_record("Parent for agent tracking", session_id=sid)
    child = _delegationlib.delegate_task("Child A", agent='codex', parent_task_id=parent_id, session_id=sid)

    child_rec = _task.load_task_record(child)
    assert child_rec.get('agent') == 'codex'


def test_aggregate_child_results(tmp_path):
    """D5: Aggregation returns counts and overall status from real child results."""
    _require_attr(_task, 'create_task_record')
    _require_attr(_task, 'set_task_result')
    _require_attr(_delegationlib, 'delegate_task')
    _require_attr(_delegationlib, 'aggregate_child_results')

    sid = 'sess-g4-d5-3'
    ensure_session(sid)
    parent_id = _task.create_task_record("Parent for aggregation", session_id=sid)

    c1 = _delegationlib.delegate_task("C1", agent='codex', parent_task_id=parent_id, session_id=sid)
    c2 = _delegationlib.delegate_task("C2", agent='claude', parent_task_id=parent_id, session_id=sid)
    c3 = _delegationlib.delegate_task("C3", agent='gemini', parent_task_id=parent_id, session_id=sid)

    _task.set_task_result(c1, status='success')
    _task.set_task_result(c2, status='failure')
    _task.set_task_result(c3, status='success')

    agg = _delegationlib.aggregate_child_results(parent_id)
    assert agg['total'] == 3
    assert agg['counts'] == {'success': 2, 'failure': 1, 'pending': 0}
    assert agg['status'] == 'partial_failure'


def test_delegation_validation_cli_missing_or_fails(tmp_path):
    """D6: Delegation validation CLI enforces required fields.

    RED phase behavior: until implemented, this should either not exist or fail.
    When implemented, it should exit 0 for valid config and non-zero for invalid.
    """
    cli_path = Path('.agents/delegation/validate')
    if not cli_path.exists():
        pytest.fail("Delegation validator CLI `.agents/delegation/validate` is missing (D6)")

    # Write an invalid config (missing required keys like roles)
    cfg_path = Path('.agents/delegation/config.json')
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps({"paths": {"docs": ".", "templates": "."}}), encoding='utf-8')

    # Execute validator expecting non-zero
    proc = run_with_timeout([str(cli_path)], capture_output=True, text=True)
    assert proc.returncode != 0, "Validator should fail for missing required fields"
    assert 'required' in (proc.stderr or proc.stdout).lower()


def test_delegation_validation_cli_passes_with_valid_config(tmp_path):
    """D6: Validator succeeds on a well-formed config."""
    cli_path = Path('.agents/delegation/validate')
    if not cli_path.exists():
        pytest.fail("Delegation validator CLI `.agents/delegation/validate` is missing (D6)")

    # Restore a minimally valid config
    cfg_path = Path('.agents/delegation/config.json')
    cfg = {
        "worktreeBase": "../{PROJECT_NAME}-worktrees",
        "roles": {"validator": "validator-codex-global"},
        "paths": {"docs": ".agents/delegation", "templates": ".edison/core/templates"}
    }
    cfg_path.write_text(json.dumps(cfg), encoding='utf-8')

    proc = run_with_timeout([str(cli_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"Expected validator to pass, got stderr: {proc.stderr} stdout: {proc.stdout}"


def test_task_session_linking(tmp_path):
    """S1: Task records link to session (task side) and session lists task.

    Validates bidirectional linkage from the task perspective.
    """
    _require_attr(_task, 'create_task_record')
    _require_attr(_task, 'load_task_record')

    sid = 'sess-g4-s1-1'
    ensure_session(sid)
    tid = _task.create_task_record("Linked task", session_id=sid)
    task = _task.load_task_record(tid)
    assert task.get('session_id') == sid

    # Session side should include the task id in its metadata (task-side responsibility to register it)
    from edison.core.sessionlib import load_session  # late import for clarity
    sess = load_session(sid)
    assert 'tasks' in sess and tid in sess['tasks']