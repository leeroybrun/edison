from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from edison.core.utils.io.locking import LockTimeoutError, acquire_file_lock
from tests.helpers.env_setup import setup_project_root
from tests.helpers.timeouts import LOCK_TIMEOUT, SHORT_SLEEP, THREAD_JOIN_TIMEOUT


def test_acquire_file_lock_can_fail_open(tmp_path: Path) -> None:
    target = tmp_path / "data.json"

    holder_ready = threading.Event()
    holder_done = threading.Event()

    def _holder() -> None:
        with acquire_file_lock(target, timeout=LOCK_TIMEOUT):
            holder_ready.set()
            time.sleep(SHORT_SLEEP * 6)  # Hold lock for a bit
            holder_done.set()

    thread = threading.Thread(target=_holder)
    thread.start()

    assert holder_ready.wait(timeout=THREAD_JOIN_TIMEOUT)
    start = time.monotonic()

    with acquire_file_lock(target, timeout=SHORT_SLEEP, fail_open=True):
        elapsed = time.monotonic() - start
        # Fail-open must return before the lock holder releases (robust vs scheduler jitter).
        assert not holder_done.is_set()
        # Safety bound: should not block for a "long" time in unit tests.
        assert elapsed < THREAD_JOIN_TIMEOUT
        target.write_text("ok", encoding="utf-8")

    thread.join()
    assert holder_done.is_set()
    assert target.read_text(encoding="utf-8") == "ok"


def test_acquire_file_lock_times_out_without_fail_open(tmp_path: Path) -> None:
    target = tmp_path / "guard.json"

    with acquire_file_lock(target, timeout=LOCK_TIMEOUT):
        with pytest.raises(LockTimeoutError):
            with acquire_file_lock(target, timeout=SHORT_SLEEP, fail_open=False):
                target.write_text("should not happen", encoding="utf-8")


def test_acquire_file_lock_uses_config_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)
    config_dir.joinpath("file-locking.yaml").write_text(
        "\n".join(
            [
                "file_locking:",
                f"  timeout_seconds: {SHORT_SLEEP}",
                f"  poll_interval_seconds: {SHORT_SLEEP / 10}",
                "  fail_open: true",
            ]
        ),
        encoding="utf-8",
    )
    setup_project_root(monkeypatch, tmp_path)

    target = tmp_path / "lock.json"
    holder_ready = threading.Event()
    holder_done = threading.Event()

    def _holder() -> None:
        with acquire_file_lock(target, timeout=LOCK_TIMEOUT):
            holder_ready.set()
            time.sleep(SHORT_SLEEP * 5)
            holder_done.set()

    thread = threading.Thread(target=_holder, daemon=True)
    thread.start()

    assert holder_ready.wait(timeout=THREAD_JOIN_TIMEOUT)

    # Warm config cache so the timing assertion reflects lock acquisition behavior,
    # not first-time config discovery/parsing overhead.
    from edison.core.utils.io.locking import get_file_locking_config

    get_file_locking_config(repo_root=tmp_path)
    start = time.monotonic()

    with acquire_file_lock(target) as fh:
        elapsed = time.monotonic() - start
        assert not holder_done.is_set()
        assert elapsed < THREAD_JOIN_TIMEOUT
        assert fh is None

    thread.join(timeout=THREAD_JOIN_TIMEOUT)
    assert not thread.is_alive()


def test_file_locking_config_exposes_yaml_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)
    config_dir.joinpath("file-locking.yaml").write_text(
        "\n".join(
            [
                "file_locking:",
                "  timeout_seconds: 0.12",
                "  poll_interval_seconds: 0.02",
                "  fail_open: false",
            ]
        ),
        encoding="utf-8",
    )
    setup_project_root(monkeypatch, tmp_path)

    from edison.core.utils.io.locking import get_file_locking_config

    cfg = get_file_locking_config(repo_root=tmp_path)
    assert cfg["timeout_seconds"] == pytest.approx(0.12)
    assert cfg["poll_interval_seconds"] == pytest.approx(0.02)
    assert cfg["fail_open"] is False
