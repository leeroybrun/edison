from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from tests.helpers.timeouts import SHORT_SLEEP, THREAD_JOIN_TIMEOUT


# Locate repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

from edison.core import task
from edison.core.session import manager as session_manager
from edison.core.session import recovery as session_recovery
from edison.core.session.repository import SessionRepository
from edison.core.session.graph import save_session
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
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    # Re-initialize module-level roots derived from environment by reloading libs
    import importlib
    import edison.core.task as _task  # type: ignore
    import edison.core.session.manager as _session_manager  # type: ignore
    import edison.core.session.recovery as _session_recovery  # type: ignore
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

    We simulate a fragile (non-atomic) writer by patching Path.write_text to
    write in two halves with a small delay between them when targeting the
    session JSON file. This widens the window where readers may observe a
    truncated/partial file. The fixed implementation must avoid corruption
    by performing atomic temp-write + fsync + replace.
    """
    sid = "atomic-race"
    monkeypatch.setenv("PROJECT_NAME", "test-project")
    session_manager.create_session(sid, owner="tester")
    dest = get_session_json_path(sid)

    # Guard: ensure file exists and is valid JSON
    assert dest.exists()
    json.loads(dest.read_text())

    # Patch Path.write_text to create a partial write window specifically for our dest
    original_write_text = Path.write_text

    def slow_write_text(self: Path, text: str, *args, **kwargs):  # type: ignore[no-redef]
        if self.resolve() == dest.resolve():
            half = max(1, len(text) // 2)
            with open(self, "w") as f:
                f.write(text[:half])
                f.flush()
                os.fsync(f.fileno())
                time.sleep(SHORT_SLEEP)  # Small window to trigger read of partial JSON
                f.write(text[half:])
                f.flush()
                os.fsync(f.fileno())
            return len(text)
        return original_write_text(self, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", slow_write_text, raising=True)

    # Spawn concurrent appenders
    errors: list[BaseException] = []
    start_barrier = threading.Barrier(10)

    def worker(idx: int) -> None:
        try:
            start_barrier.wait(timeout=5)
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

    # After the fix, there should be no JSONDecodeError or corruption
    assert not errors, f"Encountered concurrency errors: {errors!r}"
    # And final file must be valid JSON
    data = json.loads(dest.read_text())
    assert isinstance(data, dict)
    assert "activityLog" in data


def test_atomic_write_survives_interruption(sandbox_env: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify interrupted write doesn't corrupt the file.

    Simulate an exception mid-write and ensure the session file remains either
    intact (original content) or fully replaced, but never partial/corrupt.
    """
    sid = "atomic-interrupt"
    monkeypatch.setenv("PROJECT_NAME", "test-project")
    session_manager.create_session(sid, owner="tester")
    dest = get_session_json_path(sid)
    original = dest.read_text()

    class InjectedFailure(Exception):
        pass

    # Patch os.replace to simulate failure during the final atomic swap
    original_replace = os.replace

    def explode_replace(src: str, dst: str):  # type: ignore[no-redef]
        # Only fail for our session file target
        if Path(dst).resolve() == dest.resolve():
            raise InjectedFailure("boom during atomic replace")
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", explode_replace, raising=True)

    # Attempt to save; current implementation (pre-fix) will corrupt file
    with pytest.raises(InjectedFailure):
        data = json.loads(original)
        # Tweak a small field and save
        data["created_at"] = utc_timestamp()
        save_session(sid, data)

    # After the fix, the original content should remain valid JSON
    # and not be left as a partial write.
    # If implementation is still unsafe, json.loads will raise here.
    json.loads(dest.read_text())
    # Also ensure either original content or a full JSON rewrite, but not empty/partial
    assert len(dest.read_text()) >= len(original) // 2
