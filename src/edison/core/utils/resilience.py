"""Edison Framework Resilience Mechanisms.

Provides retry logic, graceful degradation, and lightweight recovery helpers.
"""

from __future__ import annotations

import time
import functools
import json
import shutil
from typing import Callable, Any, Tuple, Type
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def flaky_operation():
            # May fail transiently
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:  # type: ignore[misc]
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts")
                        raise

                    logger.warning(f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}")
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)

                    # Exponential backoff
                    delay = min(delay * backoff_factor, max_delay)

            raise RuntimeError("Unreachable")  # Should never get here

        return wrapper
    return decorator


def graceful_degradation(fallback_value: Any):
    """
    Decorator that provides graceful degradation on failure.

    Args:
        fallback_value: Value to return if function fails

    Example:
        @graceful_degradation(fallback_value=[])
        def fetch_optional_data():
            # If this fails, return empty list
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001 - broad by design for graceful fallback
                logger.warning(f"{func.__name__} failed, using fallback: {e}")
                return fallback_value

        return wrapper
    return decorator


def resume_from_recovery(recovery_dir: Path) -> Path:
    """Move a session from ``recovery`` back to ``active``.

    This is a lightweight helper used by tests to validate that sessions
    can resume after timeout handling. It operates purely on the on-disk
    layout:

        .project/sessions/recovery/<sid>/session.json
        → .project/sessions/active/<sid>/session.json

    and rewrites the ``state`` field to ``Active``.
    """
    rec_dir = Path(recovery_dir).resolve()
    if not rec_dir.exists():
        raise FileNotFoundError(f"Recovery directory not found: {rec_dir}")

    sid = rec_dir.name
    sessions_root = rec_dir.parent.parent  # .../.project/sessions
    active_root = sessions_root / "active"
    active_root.mkdir(parents=True, exist_ok=True)

    dest_dir = active_root / sid
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.move(str(rec_dir), str(dest_dir))

    sess_json = dest_dir / "session.json"
    try:
        payload = json.loads(sess_json.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    payload["state"] = "Active"
    sess_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return dest_dir
