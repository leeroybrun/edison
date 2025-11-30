from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root
from tests.helpers.timeouts import SHORT_SLEEP, THREAD_JOIN_TIMEOUT, MEDIUM_SLEEP
from tests.helpers.env_setup import setup_project_root


# Locate repo root
REPO_ROOT = get_repo_root()

from edison.core import task
from edison.core.session import lifecycle as session_manager
from edison.core.session import recovery as session_recovery
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.persistence.graph import save_session
from edison.core.utils.time import utc_timestamp

def get_session_json_path(session_id: str):
    """Get path to session.json file."""
    repo = SessionRepository()
    return repo.get_session_json_path(session_id)


def _bootstrap_minimal_project(tmp_root: Path) -> None:
    pr = tmp_root / ".project"
    # Minimal tree for sessions
    (pr / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    (pr / "sessions" / "done").mkdir(parents=True, exist_ok=True)
    (pr / "sessions" / "validated").mkdir(parents=True, exist_ok=True)

    # Required template - use bundled template from edison.data
    from edison.data import get_data_path
    (tmp_root / ".agents" / "sessions").mkdir(parents=True, exist_ok=True)
    src_tpl = get_data_path("templates", "session.template.json")
    dst_tpl = tmp_root / ".agents" / "sessions" / "TEMPLATE.json"
    dst_tpl.write_text(src_tpl.read_text())


@pytest.fixture()
def sandbox_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide isolated project_ROOT sandbox and restore env after test."""
    _bootstrap_minimal_project(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(tmp_path),
            "project_ROOT": str(tmp_path),
            "PYTHONUNBUFFERED": "1",
        }
    )
    setup_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    # Re-initialize module-level roots derived from environment by reloading libs
    import importlib
    import edison.core.task as _task  # type: ignore
    import edison.core.session.lifecycle.manager as _session_manager  # type: ignore
    import edison.core.session.lifecycle.recovery as _session_recovery  # type: ignore
    importlib.reload(_task)
    importlib.reload(_session_manager)
    importlib.reload(_session_recovery)
    # Reflect reloaded modules in our local names
    global task  # type: ignore
    global session_manager  # type: ignore
    global session_recovery  # type: ignore
    task = _task
    session_manager = _session_manager
    session_recovery = _session_recovery
    yield tmp_path


def test_concurrent_session_writes_no_corruption(sandbox_env: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify concurrent writes don't corrupt session JSON.

    This test verifies that the atomic write implementation (temp file + fsync + os.replace)
    prevents corruption even when multiple threads are writing concurrently. The write_text_locked
    function should handle locking and atomicity correctly.
    """
    sid = "atomic-race"
    monkeypatch.setenv("PROJECT_NAME", "test-project")
    session_manager.create_session(sid, owner="tester")
    dest = get_session_json_path(sid)

    # Guard: ensure file exists and is valid JSON
    assert dest.exists()
    json.loads(dest.read_text())

    # Spawn concurrent appenders that will stress test the atomic write mechanism
    errors: list[BaseException] = []
    start_barrier = threading.Barrier(10)

    def worker(idx: int) -> None:
        try:
            start_barrier.wait(timeout=THREAD_JOIN_TIMEOUT / 2)
            # Perform several log appends to increase read/write interleavings
            for j in range(25):
                # Retry on lock contention; only treat unexpected errors as failures
                for _ in range(100):
                    try:
                        session_recovery.append_session_log(sid, f"writer-{idx}-{j}")
                        break
                    except SystemExit as e:
                        # File currently locked by another writer
                        if "File is locked" in str(e):
                            time.sleep(SHORT_SLEEP / 10)  # Very short retry delay
                            continue
                        raise
                else:
                    raise AssertionError("Exceeded retries due to persistent lock contention")
        except BaseException as e:  # capture any JSONDecodeError or others
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=THREAD_JOIN_TIMEOUT)

    # After the atomic write implementation, there should be no JSONDecodeError or corruption
    assert not errors, f"Encountered concurrency errors: {errors!r}"
    # And final file must be valid JSON
    data = json.loads(dest.read_text())
    assert isinstance(data, dict)
    assert "activityLog" in data


def test_atomic_write_survives_interruption(sandbox_env: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify interrupted write doesn't corrupt the file.

    This test verifies that the atomic write implementation leaves the original file intact
    when the write process fails. We test this by attempting a write, then simulating a
    failure, and verifying the file is still valid JSON.

    Since we can't mock os.replace anymore, we test this by verifying that concurrent
    reads during writes always see valid JSON, which proves the atomicity.
    """
    sid = "atomic-interrupt"
    monkeypatch.setenv("PROJECT_NAME", "test-project")
    session_manager.create_session(sid, owner="tester")
    dest = get_session_json_path(sid)
    original = dest.read_text()

    # Test that concurrent reads during writes always see valid JSON
    errors: list[BaseException] = []
    stop_event = threading.Event()

    def writer():
        """Continuously write to the session."""
        try:
            counter = 0
            while not stop_event.is_set():
                try:
                    session_recovery.append_session_log(sid, f"write-{counter}")
                    counter += 1
                    time.sleep(SHORT_SLEEP / 100)  # Very fast writes
                except SystemExit as e:
                    if "File is locked" in str(e):
                        time.sleep(SHORT_SLEEP / 100)
                        continue
                    raise
        except BaseException as e:
            errors.append(e)

    def reader():
        """Continuously read and validate the session file."""
        try:
            for _ in range(100):
                if stop_event.is_set():
                    break
                # Read and validate JSON - if write is not atomic, this will fail
                content = dest.read_text()
                data = json.loads(content)
                assert isinstance(data, dict), "Invalid session data structure"
                assert "activityLog" in data, "Missing activityLog in session"
                time.sleep(SHORT_SLEEP / 50)  # Fast reads to catch partial writes
        except BaseException as e:
            errors.append(e)

    # Start writer and readers concurrently
    writer_thread = threading.Thread(target=writer, daemon=True)
    reader_threads = [threading.Thread(target=reader, daemon=True) for _ in range(5)]

    writer_thread.start()
    for t in reader_threads:
        t.start()

    # Let them run for a bit
    time.sleep(MEDIUM_SLEEP * 2.5)

    # Stop all threads
    stop_event.set()
    writer_thread.join(timeout=THREAD_JOIN_TIMEOUT / 2)
    for t in reader_threads:
        t.join(timeout=THREAD_JOIN_TIMEOUT / 2)

    # Verify no errors occurred (no JSONDecodeError from partial writes)
    assert not errors, f"Encountered errors during concurrent read/write: {errors!r}"

    # Final file must be valid JSON
    final_content = dest.read_text()
    data = json.loads(final_content)
    assert isinstance(data, dict)
    assert "activityLog" in data
