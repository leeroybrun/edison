from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from edison.core.utils.io.locking import LockTimeoutError, acquire_file_lock
from tests.helpers.timeouts import SHORT_SLEEP, LOCK_TIMEOUT, THREAD_JOIN_TIMEOUT
from tests.helpers.env_setup import setup_project_root


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
        # Fail-open should return quickly instead of blocking for holder duration
        assert elapsed < (SHORT_SLEEP * 4)
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
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    config_dir.joinpath("defaults.yaml").write_text(
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

    def _holder() -> None:
        with acquire_file_lock(target, timeout=LOCK_TIMEOUT):
            holder_ready.set()
            time.sleep(SHORT_SLEEP * 5)

    thread = threading.Thread(target=_holder, daemon=True)
    thread.start()

    assert holder_ready.wait(timeout=THREAD_JOIN_TIMEOUT)
    start = time.monotonic()

    with acquire_file_lock(target) as fh:
        elapsed = time.monotonic() - start
        # Should respect config timeout+fail_open and return quickly without the lock.
        assert elapsed < (SHORT_SLEEP * 3)
        assert fh is None

    thread.join(timeout=THREAD_JOIN_TIMEOUT)
    assert not thread.is_alive()


def test_file_locking_config_exposes_yaml_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    config_dir.joinpath("defaults.yaml").write_text(
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

    # Reload to ensure the module observes the temp project root and config
    import importlib
    from edison.core.utils.io import locking

    locking = importlib.reload(locking)

    cfg = locking.get_file_locking_config()  # type: ignore[attr-defined]
    assert cfg["timeout_seconds"] == pytest.approx(0.12)
    assert cfg["poll_interval_seconds"] == pytest.approx(0.02)
    assert cfg["fail_open"] is False
