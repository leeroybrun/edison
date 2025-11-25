from __future__ import annotations

"""Lock utilities, safe moves, and transactional write helpers."""

import errno
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from ..locklib import acquire_file_lock, LockTimeoutError
from ..utils.subprocess import run_with_timeout
from .paths import ROOT

# Fallback when resilience is unavailable (kept for compatibility in partial installs)
try:  # pragma: no cover - defensive import
    from ..resilience import retry_with_backoff  # type: ignore
except Exception:  # noqa: BLE001
    def retry_with_backoff(
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        def decorator(fn):
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            return wrapper

        return decorator


def _load_retry_config() -> dict:
    defaults = {
        "max_attempts": 3,
        "initial_delay_seconds": 1.0,
        "backoff_factor": 2.0,
        "max_delay_seconds": 60.0,
    }
    try:
        from edison.data import get_data_path
        import yaml  # type: ignore

        cfg_path = get_data_path("config", "defaults.yaml")
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            r = (data.get("resilience") or {}).get("retry") or {}
            defaults.update(
                {
                    "max_attempts": int(r.get("max_attempts", defaults["max_attempts"])),
                    "initial_delay_seconds": float(
                        r.get("initial_delay_seconds", defaults["initial_delay_seconds"])
                    ),
                    "backoff_factor": float(r.get("backoff_factor", defaults["backoff_factor"])),
                    "max_delay_seconds": float(r.get("max_delay_seconds", defaults["max_delay_seconds"])),
                }
            )
    except Exception:
        pass
    return defaults


_RETRY_CFG = _load_retry_config()


def _safe_git_command(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
):
    """Run a git command with retry/backoff and consistent defaults."""

    @retry_with_backoff(
        max_attempts=_RETRY_CFG["max_attempts"],
        initial_delay=_RETRY_CFG["initial_delay_seconds"],
        backoff_factor=_RETRY_CFG["backoff_factor"],
        max_delay=_RETRY_CFG["max_delay_seconds"],
        exceptions=(subprocess.CalledProcessError,),
    )
    def _run():
        return run_with_timeout(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=text,
        )

    return _run()


def _lockfile_path(target: Path) -> Path:
    target = Path(target)
    return target.with_suffix(target.suffix + ".lock")


def is_locked(target: Path) -> bool:
    """Return True when a lock file exists for target."""
    return _lockfile_path(target).exists()


@contextmanager
def file_lock(target: Path, timeout: float = 10.0):
    """Create an exclusive lock for the target using sidecar .lock file."""
    try:
        with acquire_file_lock(Path(target), timeout=timeout):
            yield target
    except LockTimeoutError as e:  # pragma: no cover - error path validated by session tests
        raise SystemExit(f"File is locked: {target}") from e


def safe_move_file(path: Path, destination: Path) -> Path:
    """Atomically move a file, preferring git mv -- when available."""
    src = Path(path)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = _safe_git_command(
            ["git", "mv", "--", str(src), str(dest)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return dest
    except Exception:
        pass

    try:
        os.replace(str(src), str(dest))
        return dest
    except OSError as e:
        if e.errno == errno.EXDEV:
            # Cross-device move: copy + verify + delete
            shutil.copy2(str(src), str(dest))
            # Verify by comparing content (not just size) to detect corruption
            src_content = src.read_bytes()
            dest_content = dest.read_bytes()
            if src_content != dest_content:
                dest.unlink(missing_ok=True)
                raise RuntimeError("Cross-device move verification failed - content mismatch") from e
            src.unlink(missing_ok=True)
            return dest
        raise


def write_text_locked(path: Path, content: str) -> None:
    """Write text atomically while holding an exclusive lock on the target."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp: Optional[Path] = None
    with file_lock(target):
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(target.parent), delete=False
            ) as fh:
                tmp = Path(fh.name)
                fh.write(content)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(str(tmp), str(target))
        finally:
            if tmp is not None and tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    pass


@contextmanager
def transactional_move(
    path: Path,
    record_type: str,
    status: str,
    session_id: Optional[str] = None,
):
    """Context manager to move a record with rollback on failure."""
    from .io import move_to_status  # local import to avoid circular dependency

    original = Path(path).resolve()
    new_path = move_to_status(original, record_type, status, session_id=session_id)
    try:
        yield new_path
    except Exception:
        try:
            safe_move_file(new_path, original)
        except Exception:
            pass
        raise


__all__ = [
    "is_locked",
    "file_lock",
    "safe_move_file",
    "transactional_move",
    "write_text_locked",
]
