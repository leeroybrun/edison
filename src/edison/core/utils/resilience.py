"""Edison Framework Resilience Mechanisms.

Provides retry logic, graceful degradation, and lightweight recovery helpers.
"""

from __future__ import annotations

import time
import functools
import shutil
from typing import Callable, Any, Tuple, Type, Optional, Dict
from pathlib import Path
import logging

from edison.core.file_io import utils as io_utils

logger = logging.getLogger(__name__)


def get_retry_config() -> Dict[str, Any]:
    """Load retry configuration from YAML-driven settings.

    Returns:
        Dict[str, Any]: Mapping containing retry settings with safe fallbacks.
    """
    from edison.core.config import ConfigManager

    mgr = ConfigManager()
    cfg = mgr.load_config()
    retry_cfg = cfg.get("resilience", {}).get("retry", {}) if isinstance(cfg, dict) else {}

    return {
        "max_attempts": retry_cfg.get("max_attempts", 3),
        "initial_delay": retry_cfg.get("initial_delay_seconds", 1.0),
        "backoff_factor": retry_cfg.get("backoff_factor", 2.0),
        "max_delay": retry_cfg.get("max_delay_seconds", 60.0),
    }


def retry_with_backoff(
    max_attempts: Optional[int] = None,
    initial_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    max_delay: Optional[float] = None,
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
    config = get_retry_config()

    effective_max_attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    effective_initial_delay = initial_delay if initial_delay is not None else config["initial_delay"]
    effective_backoff_factor = backoff_factor if backoff_factor is not None else config["backoff_factor"]
    effective_max_delay = max_delay if max_delay is not None else config["max_delay"]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = effective_initial_delay
            for attempt in range(1, effective_max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:  # type: ignore[misc]
                    if attempt == effective_max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {effective_max_attempts} attempts"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{effective_max_attempts} failed: {e}"
                    )
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)

                    # Exponential backoff
                    delay = min(delay * effective_backoff_factor, effective_max_delay)

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
    io_utils.ensure_dir(active_root)

    dest_dir = active_root / sid
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.move(str(rec_dir), str(dest_dir))

    sess_json = dest_dir / "session.json"
    payload = io_utils.read_json_safe(sess_json, default={})
    if not isinstance(payload, dict):
        payload = {}
        
    payload["state"] = "Active"
    io_utils.write_json_safe(sess_json, payload, ensure_ascii=False)
    return dest_dir
