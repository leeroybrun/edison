"""Session transaction API tests for sessionlib.

Covers:
- Commit / rollback via high-level helpers
- Context-managed session_transaction wrapper
- Nested transactions
- Concurrency / lock conflict behavior
- Crash-style recovery using commit_tx / rollback_tx
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_DIR = REPO_ROOT / ".edison" / "core"

if str(CORE_DIR) not in os.sys.path:

from edison.core import task  # type: ignore  # pylint: disable=wrong-import-position
from edison.core.session import transaction as session_transaction
from edison.core.session import store as session_store
from edison.core.locklib import acquire_file_lock, LockTimeoutError
from edison.core.io_utils import read_json_safe as io_read_json_safe  # type: ignore  # pylint: disable=wrong-import-position


def _bootstrap_minimal_project(tmp_root: Path) -> None:
    """Create the minimal directory/layout needed for sessionlib."""
    pr = tmp_root / ".project"
    # Minimal sessions tree
    (pr / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    # TX root will be created on demand under .project/sessions/_tx

    # Required session template
    (tmp_root / ".agents" / "sessions").mkdir(parents=True, exist_ok=True)
    src_tpl = REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json"
    dst_tpl = tmp_root / ".agents" / "sessions" / "TEMPLATE.json"
    shutil.copyfile(src_tpl, dst_tpl)


@pytest.fixture()
def sandbox_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide isolated project root and reload libs against it."""
    _bootstrap_minimal_project(tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))

    # Reload task/sessionlib so their ROOT/DATA_ROOT/TX_ROOT derive from sandbox
    import importlib

    import edison.core.task as _task  # type: ignore
    import edison.core.session.transaction as _session_transaction  # type: ignore
    import edison.core.session.store as _session_store  # type: ignore

    importlib.reload(_task)
    importlib.reload(_session_transaction)
    importlib.reload(_session_store)

    global task  # type: ignore
    global session_transaction  # type: ignore
    global session_store  # type: ignore
    task = _task
    session_transaction = _session_transaction
    session_store = _session_store

    yield tmp_path


@pytest.mark.session
@pytest.mark.fast
def test_session_transaction_commit_and_rollback(sandbox_env: Path):
    """session_transaction commits on success and rolls back on error."""
    sid = "tx-session-commit-rollback"

    # Commit path: no exception → finalizedAt set, no abortedAt
    with session_transaction.session_transaction(
        sid,
        domain="task",
        record_id="T-1",
        from_status="todo",
        to_status="wip",
    ) as tx_id:
        tx_file = session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{tx_id}.json"
        assert tx_file.exists()
        data = io_read_json_safe(tx_file)
        assert data.get("txId") == tx_id
        assert data.get("sessionId") == session_store.sanitize_session_id(sid)
        assert data.get("finalizedAt") is None
        assert data.get("abortedAt") is None

    data = io_read_json_safe(
        session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{tx_id}.json"
    )
    assert data.get("finalizedAt") is not None
    assert data.get("abortedAt") is None

    # Rollback path: exception inside context → abortedAt set, no finalizedAt
    sid2 = "tx-session-rollback"
    with pytest.raises(RuntimeError):
        with session_transaction.session_transaction(
            sid2,
            domain="task",
            record_id="T-2",
            from_status="wip",
            to_status="blocked",
        ) as tx2:
            tx_file2 = session_transaction._tx_dir(session_store.sanitize_session_id(sid2)) / f"{tx2}.json"
            assert tx_file2.exists()
            raise RuntimeError("force rollback")

    data2 = io_read_json_safe(
        session_transaction._tx_dir(session_store.sanitize_session_id(sid2)) / f"{tx2}.json"
    )
    assert data2.get("abortedAt") is not None
    assert data2.get("finalizedAt") is None


@pytest.mark.session
@pytest.mark.fast
def test_session_transaction_nested_transactions(sandbox_env: Path):
    """Nested session_transaction blocks each journal their own tx safely."""
    sid = "tx-session-nested"

    with session_transaction.session_transaction(sid, domain="task", record_id="outer", from_status="todo", to_status="wip") as outer_tx:
        with session_transaction.session_transaction(sid, domain="task", record_id="inner", from_status="wip", to_status="done") as inner_tx:
            outer_file = session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{outer_tx}.json"
            inner_file = session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{inner_tx}.json"
            assert outer_file.exists()
            assert inner_file.exists()

    outer_data = io_read_json_safe(
        session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{outer_tx}.json"
    )
    inner_data = io_read_json_safe(
        session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{inner_tx}.json"
    )
    assert outer_data.get("finalizedAt") is not None
    assert inner_data.get("finalizedAt") is not None


@pytest.mark.session
@pytest.mark.fast
def test_commit_and_rollback_tx_respect_locks(sandbox_env: Path):
    """commit_tx must respect file locks like finalize_tx."""
    sid = "tx-session-locks"
    tx_id = session_transaction.begin_tx(
        sid,
        domain="task",
        record_id="R-1",
        from_status="todo",
        to_status="wip",
    )
    tx_file = session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{tx_id}.json"
    assert tx_file.exists()

    # Hold lock and ensure commit_tx propagates LockTimeoutError (raw locklib behavior)
    with acquire_file_lock(tx_file):
        with pytest.raises(LockTimeoutError):
            session_transaction.commit_tx(tx_id)


@pytest.mark.session
@pytest.mark.fast
def test_commit_and_rollback_support_crash_recovery(sandbox_env: Path):
    """commit_tx / rollback_tx can be called with only tx_id (no session_id)."""
    sid = "tx-session-recover"
    # Begin transaction but do not finalize/abort (simulate crash before close)
    tx_id = session_transaction.begin_tx(
        sid,
        domain="task",
        record_id="R-2",
        from_status="todo",
        to_status="wip",
    )
    tx_file = session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{tx_id}.json"
    assert tx_file.exists()

    # Crash recovery via commit_tx using only tx_id
    session_transaction.commit_tx(tx_id)
    data = io_read_json_safe(
        session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{tx_id}.json"
    )
    assert data.get("finalizedAt") is not None

    # New tx for rollback path
    tx_id2 = session_transaction.begin_tx(
        sid,
        domain="task",
        record_id="R-3",
        from_status="todo",
        to_status="wip",
    )
    session_transaction.rollback_tx(tx_id2)
    data2 = io_read_json_safe(
        session_transaction._tx_dir(session_store.sanitize_session_id(sid)) / f"{tx_id2}.json"
    )
    assert data2.get("abortedAt") is not None
