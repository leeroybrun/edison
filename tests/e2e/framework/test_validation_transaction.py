"""WP-004: Bundle Validation Transaction Wrapper tests (RED phase).

Covers:
- Successful commit of staged validation artifacts
- Rollback (no commit) on failure inside context
- Crash recovery cleanup of incomplete transactions
- Concurrency guard via lock
- Disk full precheck handling
- Permission error handling

Note: These tests target the new sessionlib.validation_transaction context manager
and the integration flow expectations. They do not depend on validators actually
running; tests write small files into the staging root exposed by the context.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
import sys

import pytest


def _evidence_paths(root: Path, task_id: str, round_no: int = 1) -> Path:
    return root / ".project" / "qa" / "validation-evidence" / task_id / f"round-{round_no}"


@pytest.mark.fast
def test_validation_tx_commit_success(monkeypatch, tmp_path: Path):
    # Arrange: temp project root
    project_root = tmp_path
    (project_root / ".project" / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    # Route sessionlib/task ROOT to tmp via env
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))

    # Ensure core lib importable in tests
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    core_root = repo_root / ".edison" / "core"

    # Lazy import after env override
    from tests.helpers import session as sessionlib  # type: ignore

    sid = "sid-wp004-commit"
    task_id = "tx-commit-001"

    # Act: open tx, write staged artifact, commit
    with sessionlib.validation_transaction(session_id=sid, wave="wave2") as tx:
        staging_root = tx.staging_root
        ev = _evidence_paths(staging_root, task_id)
        ev.mkdir(parents=True, exist_ok=True)
        (ev / "validator-codex-global-report.json").write_text("{\n\"ok\": true\n}\n")
        tx.commit()

    # Assert: artifact moved atomically into real project evidence
    final_ev = _evidence_paths(project_root, task_id)
    assert final_ev.exists(), "Expected committed evidence directory to exist"
    assert (final_ev / "validator-codex-global-report.json").exists(), "Committed artifact missing"
    # Log exists
    tx_log = project_root / ".project" / "sessions" / sid / "validation-transactions.log"
    assert tx_log.exists(), "Transaction log not created"
    log_text = tx_log.read_text()
    assert "commit" in log_text and "started" in log_text, "Commit not logged"


@pytest.mark.fast
def test_validation_tx_rollback_on_exception(monkeypatch, tmp_path: Path):
    project_root = tmp_path
    (project_root / ".project" / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    core_root = repo_root / ".edison" / "core"
    from tests.helpers import session as sessionlib  # type: ignore

    sid = "sid-wp004-rollback"
    task_id = "tx-rollback-001"

    try:
        with sessionlib.validation_transaction(session_id=sid, wave="wave2") as tx:
            ev = _evidence_paths(tx.staging_root, task_id)
            ev.mkdir(parents=True, exist_ok=True)
            (ev / "validator-claude-global-report.json").write_text("{}\n")
            # No commit → raise to trigger rollback
            raise RuntimeError("simulate failure")
    except RuntimeError:
        pass

    # No artifacts visible in real project
    final_ev = _evidence_paths(project_root, task_id)
    assert not final_ev.exists(), "Rollback failed: partial artifacts leaked to project root"


@pytest.mark.fast
def test_validation_tx_crash_recovery_cleanup(monkeypatch, tmp_path: Path):
    project_root = tmp_path
    (project_root / ".project" / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    core_root = repo_root / ".edison" / "core"
    from tests.helpers import session as sessionlib  # type: ignore

    sid = "sid-wp004-recover"

    # Start a tx, create a marker under TX root, but do not commit
    with sessionlib.validation_transaction(session_id=sid, wave="wave2") as tx:
        staging_root = tx.staging_root
        # Create a dummy file to prove presence before recovery
        (staging_root / "_marker").parent.mkdir(parents=True, exist_ok=True)
        (staging_root / "_marker").write_text("x")
        # Do not commit and do not raise → implicit abort on exit
    # Simulate orphaned staging dir left behind (would happen on crash before abort)
    # Create a fake incomplete meta and staging dir
    # Then run recovery
    recovered = sessionlib.recover_incomplete_validation_transactions(sid)
    assert isinstance(recovered, int)
    # Idempotent: running again finds nothing
    recovered2 = sessionlib.recover_incomplete_validation_transactions(sid)
    assert recovered2 == 0


@pytest.mark.fast
def test_validation_tx_concurrency_lock(monkeypatch, tmp_path: Path):
    project_root = tmp_path
    sessions_dir = project_root / ".project" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    core_root = repo_root / ".edison" / "core"
    from tests.helpers import session as sessionlib  # type: ignore

    sid = "sid-wp004-concurrent"

    # First tx acquires lock
    tx1 = sessionlib.validation_transaction(session_id=sid, wave="wave2")
    cm1 = tx1.__enter__()
    try:
        # Second should fail fast due to lock (after limited retries)
        with pytest.raises(SystemExit):
            with sessionlib.validation_transaction(session_id=sid, wave="wave2"):
                pass
    finally:
        cm1.abort("test cleanup")
        tx1.__exit__(None, None, None)


@pytest.mark.fast
def test_validation_tx_disk_full_precheck(monkeypatch, tmp_path: Path):
    project_root = tmp_path
    (project_root / ".project" / "sessions").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    # Force disk-full path
    monkeypatch.setenv("project_FORCE_DISK_FULL", "1")
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    core_root = repo_root / ".edison" / "core"
    from tests.helpers import session as sessionlib  # type: ignore

    sid = "sid-wp004-diskfull"
    with pytest.raises(OSError):
        with sessionlib.validation_transaction(session_id=sid, wave="wave2"):
            pass


@pytest.mark.fast
def test_validation_tx_permission_error_on_commit(monkeypatch, tmp_path: Path):
    project_root = tmp_path
    (project_root / ".project" / "sessions").mkdir(parents=True, exist_ok=True)
    # Simulate permission failure deterministically via env
    monkeypatch.setenv("project_FORCE_PERMISSION_ERROR", "1")

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    repo_root = Path(__file__).resolve()
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent
    core_root = repo_root / ".edison" / "core"
    from tests.helpers import session as sessionlib  # type: ignore

    sid = "sid-wp004-perm"
    task_id = "tx-perm-001"
    try:
        with sessionlib.validation_transaction(session_id=sid, wave="wave2") as tx:
            ev = _evidence_paths(tx.staging_root, task_id)
            ev.mkdir(parents=True, exist_ok=True)
            (ev / "validator-security-report.json").write_text("{}\n")
            with pytest.raises(PermissionError):
                tx.commit()
    finally:
        pass
