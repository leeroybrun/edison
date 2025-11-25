from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from typing import Tuple

import pytest
import yaml


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


@pytest.fixture
def mgmt_repo(tmp_path: Path, monkeypatch) -> Tuple[Path, Path]:
    """Create a real repo with custom management dir (.mgmt) and no .project."""
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    mgmt = tmp_path / ".mgmt"
    for rel in [
        "tasks/todo",
        "tasks/wip",
        "qa/validation-evidence",
        "qa/waiting",
        "sessions/wip",
        "sessions/active",
        "logs",
        "archive",
        "sessions/_tx",
    ]:
        (mgmt / rel).mkdir(parents=True, exist_ok=True)

    # Seed minimal session records so session/store lookups succeed
    for sid in ("sess-1", "validation-session"):
        sess_dir = mgmt / "sessions" / "wip" / sid
        sess_dir.mkdir(parents=True, exist_ok=True)
        (sess_dir / "session.json").write_text(
            json.dumps({"id": sid, "state": "wip", "meta": {}, "tasks": {}, "qa": {}}),
            encoding="utf-8",
        )

    # Config: point management dir to .mgmt and session paths into it
    _write_yaml(
        tmp_path / ".agents" / "config.yml",
        {"paths": {"management_dir": ".mgmt"}, "session": {"paths": {"root": ".mgmt/sessions", "archive": ".mgmt/archive", "tx": ".mgmt/sessions/_tx"}}},
    )
    _write_yaml(
        tmp_path / ".edison" / "core" / "config" / "defaults.yaml",
        {
            "paths": {"project_config_dir": ".agents"},
            "session": {"paths": {"root": ".mgmt/sessions", "archive": ".mgmt/archive", "tx": ".mgmt/sessions/_tx"}},
        },
    )

    return tmp_path, mgmt


def test_questionnaire_defaults_pick_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    from edison.core.setup.questionnaire import SetupQuestionnaire

    q = SetupQuestionnaire(repo_root=repo, edison_core=Path(__file__).resolve().parents[2])
    ctx = q._context_with_defaults({})
    assert ctx.get("project_management_dir") == str(mgmt.relative_to(repo))


def test_resolver_project_path_uses_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.paths.resolver as resolver

    importlib.reload(resolver)
    path = resolver.PathResolver.get_project_path("tasks")
    assert path == mgmt / "tasks"


def test_qa_store_root_uses_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.qa.store as store

    importlib.reload(store)
    assert store.qa_root(repo) == mgmt / "qa"


def test_sessionlib_audit_log_writes_under_management_logs(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.sessionlib as sessionlib

    importlib.reload(sessionlib)
    sessionlib._audit_log("wip", "done", "sess-1", "moved")  # type: ignore[attr-defined]
    assert (mgmt / "logs" / "state-transitions.jsonl").exists()


def test_task_io_records_evidence_in_management_dir(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.task.paths as task_paths
    import edison.core.task.io as task_io

    importlib.reload(task_paths)
    importlib.reload(task_io)
    path = task_io.record_tdd_evidence("42", "red", note="failing first")
    assert str(path).startswith(str((mgmt / "qa" / "validation-evidence" / "tasks").resolve()))


def test_task_context7_scans_management_tasks(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    task_file = mgmt / "tasks" / "todo" / "task-1.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("# Task\n\n## Primary Files / Areas\n- src/app.py\n", encoding="utf-8")

    import edison.core.task.paths as task_paths
    import edison.core.task.context7 as ctx7

    importlib.reload(task_paths)
    importlib.reload(ctx7)
    candidates = ctx7._collect_candidate_files(task_file, session=None)
    assert "src/app.py" in candidates


def test_evidence_manager_base_dir_under_management_root(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.evidence as evidence

    importlib.reload(evidence)
    mgr = evidence.EvidenceManager("task-9")
    assert str(mgr.base_dir).startswith(str(mgmt / "qa" / "validation-evidence"))


def test_session_validation_transaction_stages_under_management(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.session.store as session_store
    import edison.core.session.transaction as session_tx

    importlib.reload(session_store)
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
    import edison.core.session.autostart as autostart

    importlib.reload(autostart)
    sa = autostart.SessionAutoStart(project_root=repo)
    path = sa._session_log_path("sess-99")
    assert str(path).startswith(str(mgmt / "sessions" / "wip" / "sess-99"))


def test_qa_validation_transaction_staging_under_management(mgmt_repo: Tuple[Path, Path]) -> None:
    repo, mgmt = mgmt_repo
    import edison.core.session.store as session_store
    import edison.core.qa.transaction as qa_tx

    importlib.reload(session_store)
    importlib.reload(qa_tx)
    tx = qa_tx.ValidationTransaction("task-2", 1)
    tx.begin()
    assert str(tx.staging_dir).startswith(str(mgmt))
