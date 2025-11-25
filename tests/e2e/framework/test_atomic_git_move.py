from __future__ import annotations

import errno
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Ensure script lib path importable
def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root")

REPO_ROOT = get_repo_root()
SCRIPTS_ROOT = REPO_ROOT / ".edison" / "core"
from edison.core import task  # type: ignore  # pylint: disable=wrong-import-position


@pytest.fixture()
def tmp_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Make task resolve ROOT to tmp_path for any relative usage
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("hello\n")
    if dst.exists():
        dst.unlink()
    return src, dst


def _fail_git_mv(*args, **kwargs):
    raise subprocess.CalledProcessError(returncode=1, cmd=kwargs.get("args") or args)


def test_atomic_move_no_duplicates(tmp_files, monkeypatch: pytest.MonkeyPatch):
    """Verify atomic move doesn't leave duplicates (git mv disabled)."""
    src, dst = tmp_files

    # Disable git mv so fallback is exercised
    monkeypatch.setattr(task.subprocess, "run", _fail_git_mv)

    # Perform move
    task.safe_move_file(src, dst)

    # Only destination should exist
    assert dst.exists()
    assert not src.exists()


def test_cross_device_move_verified(tmp_files, monkeypatch: pytest.MonkeyPatch):
    """Verify cross-device moves are verified before delete."""
    src, dst = tmp_files

    # Force git mv failure
    monkeypatch.setattr(task.subprocess, "run", _fail_git_mv)

    # Force EXDEV on atomic replace
    def exdev_replace(s, d):
        err = OSError("cross-device move")
        err.errno = errno.EXDEV
        raise err

    monkeypatch.setattr(task.os, "replace", exdev_replace)

    # Spy on read_bytes calls to ensure verification happened
    real_read = Path.read_bytes
    reads: list[str] = []

    def traced_read(self: Path) -> bytes:
        data = real_read(self)
        reads.append(self.name)
        return data

    monkeypatch.setattr(Path, "read_bytes", traced_read, raising=True)

    task.safe_move_file(src, dst)

    # Destination exists, source removed, and both were read for verification
    assert dst.exists()
    assert not src.exists()
    assert src.name in reads and dst.name in reads


def test_failed_verification_cleans_up(tmp_files, monkeypatch: pytest.MonkeyPatch):
    """Verify failed verification doesn't leave partial copy and keeps source."""
    src, dst = tmp_files

    # Force git mv failure and EXDEV path
    monkeypatch.setattr(task.subprocess, "run", _fail_git_mv)

    def exdev_replace(s, d):
        err = OSError("cross-device move")
        err.errno = errno.EXDEV
        raise err

    monkeypatch.setattr(task.os, "replace", exdev_replace)

    # Corrupt destination verification by altering read_bytes for dst only
    real_read = Path.read_bytes

    def corrupted_read(self: Path) -> bytes:
        data = real_read(self)
        if self == dst and data:
            return data + b"corrupt"
        return data

    monkeypatch.setattr(Path, "read_bytes", corrupted_read, raising=True)

    with pytest.raises(RuntimeError):
        task.safe_move_file(src, dst)

    # Destination cleaned up; source preserved
    assert not dst.exists()
    assert src.exists()


def test_git_mv_preferred_when_available(tmp_files, monkeypatch: pytest.MonkeyPatch):
    """Verify git mv is used when available with -- separator."""
    src, dst = tmp_files

    calls: dict[str, int] = {"git_mv": 0}

    real_replace = os.replace

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        # Expect git mv with -- separator
        if isinstance(args, (list, tuple)) and len(args) >= 4 and args[0] == "git" and args[1] == "mv":
            assert args[2] == "--", "git mv must include '--' separator"
            calls["git_mv"] += 1
            # Simulate a successful move
            real_replace(args[3], args[4])
            class P:
                returncode = 0
                stdout = ""
                stderr = ""
            return P()
        raise AssertionError("Unexpected subprocess.run call in test")

    monkeypatch.setattr(task.subprocess, "run", fake_run)

    task.safe_move_file(src, dst)

    assert calls["git_mv"] == 1
    assert dst.exists() and not src.exists()
