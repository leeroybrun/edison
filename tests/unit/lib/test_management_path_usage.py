from __future__ import annotations
from helpers.io_utils import write_yaml

import importlib
import json
import subprocess
from pathlib import Path
from typing import Tuple

import pytest

from tests.config import get_task_states, get_qa_states, get_session_states
from tests.helpers.env_setup import setup_project_root

@pytest.fixture
def mgmt_repo(tmp_path: Path, monkeypatch) -> Tuple[Path, Path]:
    """Create a real repo with custom management dir (.mgmt) and no .project."""
    setup_project_root(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    mgmt = tmp_path / ".mgmt"

    # Load state directories from config (NO hardcoded values)
    task_states = get_task_states()
    qa_states = get_qa_states()
    session_states = get_session_states()

    # Create task directories
    for state in task_states:
        (mgmt / "tasks" / state).mkdir(parents=True, exist_ok=True)

    # Create QA directories
    for state in qa_states:
        (mgmt / "qa" / state).mkdir(parents=True, exist_ok=True)
    (mgmt / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

    # Create session directories
    for state in session_states:
        (mgmt / "sessions" / state).mkdir(parents=True, exist_ok=True)

    # Create additional directories
    for rel in ["logs", "archive", "sessions/_tx"]:
        (mgmt / rel).mkdir(parents=True, exist_ok=True)

    # Seed minimal session records so session/store lookups succeed
    for sid in ("sess-1", "validation-session"):
        sess_dir = mgmt / "sessions" / "wip" / sid
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "session.json").write_text(
            json.dumps({"id": sid, "state": "wip", "meta": {}, "tasks": {}, "qa": {}}),
            encoding="utf-8",
        )

    # Config: point project config dir to .agents, then point management dir to .mgmt
    write_yaml(
        tmp_path / ".edison" / "config" / "paths.yaml",
        {"paths": {"project_config_dir": ".agents"}},
    )
    write_yaml(
        tmp_path / ".agents" / "config.yml",
        {"paths": {"management_dir": ".mgmt"}},
    )
    write_yaml(
        tmp_path / ".agents" / "config" / "session.yaml",
        {"session": {"paths": {"root": ".mgmt/sessions", "archive": ".mgmt/archive", "tx": ".mgmt/sessions/_tx"}}},
    )

    return tmp_path, mgmt

def test_questionnaire_defaults_pick_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    from edison.core.setup import SetupQuestionnaire
    from edison.core.setup.questionnaire.context import build_context_with_defaults
    import edison.core.utils.paths.management as mgmt_pkg

    # Reset singleton to pick up new config
    mgmt_pkg._paths_instance = None

    q = SetupQuestionnaire(repo_root=repo, edison_core=Path(__file__).resolve().parents[2])
    ctx = build_context_with_defaults(q, {})
    assert ctx.get("project_management_dir") == str(mgmt.relative_to(repo))

def test_resolver_project_path_uses_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.utils.paths.resolver as resolver

    importlib.reload(resolver)
    path = resolver.PathResolver.get_project_path("tasks")
    assert path == mgmt / "tasks"

def test_qa_store_root_uses_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    from edison.core.utils.paths.management import get_management_paths

    mgmt_paths = get_management_paths(repo)
    assert mgmt_paths.get_qa_root() == mgmt / "qa"

@pytest.mark.skip(reason="Legacy _audit_log function removed during Wave 7 module cleanup")
def test_sessionlib_audit_log_writes_under_management_logs(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    # NOTE: _audit_log was removed as part of the session module cleanup.
    # Audit logging is now handled differently within the session store.
    pass

@pytest.mark.skip(reason="record_tdd_evidence removed - legacy io.py deleted in cleanup")
def test_task_io_records_evidence_in_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    # This test validated that record_tdd_evidence wrote to the correct management dir.
    # The function was removed as part of legacy task.io cleanup.
    # Evidence recording is now handled by edison.core.qa.evidence.service
    pass

def test_task_context7_scans_management_tasks(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    task_file = mgmt / "tasks" / "todo" / "task-1.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("# Task\n\n## Primary Files / Areas\n- src/app.py\n", encoding="utf-8")

    import edison.core.task.paths as task_paths
    import edison.core.qa.context.context7 as ctx7

    importlib.reload(task_paths)
    importlib.reload(ctx7)
    candidates = ctx7._collect_candidate_files(task_file, session=None)
    assert "src/app.py" in candidates

def test_evidence_service_root_under_management_root(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.utils.paths.management as mgmt_pkg
    import edison.core.qa.evidence.service as evidence_service

    # Reset singleton to pick up new config
    mgmt_pkg._paths_instance = None
    
    importlib.reload(evidence_service)
    
    svc = evidence_service.EvidenceService("task-9", project_root=repo)
    assert str(svc.get_evidence_root()).startswith(str(mgmt / "qa" / "validation-evidence"))

def test_session_validation_transaction_stages_under_management(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.session.lifecycle.transaction as session_tx
    import edison.core.session._config as session_config

    # Clear the config cache to pick up new configuration
    session_config.get_config.cache_clear()
    importlib.reload(session_tx)
    tx = session_tx.ValidationTransaction("sess-1", "task-1")
    assert str(tx.staging_root).startswith(str(mgmt))

def test_session_next_scans_management_tasks(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    task_file = mgmt / "tasks" / "todo" / "001-demo.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("---\nid: 001-demo\n---\n", encoding="utf-8")

    import edison.core.task.paths as task_paths
    importlib.reload(task_paths)

    import edison.core.task as task_pkg
    importlib.reload(task_pkg)

    import edison.core.session.next as session_next

    importlib.reload(session_next)
    files = session_next._all_task_files()
    assert task_file.resolve() in files

def test_session_autostart_logs_under_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    from edison.core.session.lifecycle import autostart

    importlib.reload(autostart)
    sa = autostart.SessionAutoStart(project_root=repo)
    path = sa._session_log_path("sess-99")
    assert str(path).startswith(str(mgmt / "sessions" / "wip" / "sess-99"))

def test_qa_validation_transaction_staging_under_management(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.qa.workflow.transaction as qa_tx

    importlib.reload(qa_tx)
    tx = qa_tx.ValidationTransaction("task-2", 1)
    tx.begin()
    assert str(tx.staging_dir).startswith(str(mgmt))
