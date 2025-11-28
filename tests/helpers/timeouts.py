"""Centralized test timeout configuration.

All test timeouts should use these configurable values to work reliably
in slow CI environments and different hardware configurations.

Environment variables:
- TEST_TIMEOUT_MULTIPLIER: Multiply all timeouts by this factor (default: 1.0)
- TEST_FILE_WAIT_TIMEOUT: Timeout for file existence checks (default: 10.0)
- TEST_POLL_INTERVAL: Poll interval for file/state checks (default: 0.1)
- TEST_SUBPROCESS_TIMEOUT: Timeout for subprocess operations (default: 120)
- TEST_THREAD_JOIN_TIMEOUT: Timeout for thread joins (default: 10.0)
- TEST_LOCK_TIMEOUT: Timeout for file lock operations (default: 2.0)
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable


def _get_float_env(name: str, default: float) -> float:
    """Get float from environment variable with fallback."""
    try:
        return float(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default


def _get_int_env(name: str, default: int) -> int:
    """Get int from environment variable with fallback."""
    try:
        return int(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default


# Global timeout multiplier for CI environments
TIMEOUT_MULTIPLIER = _get_float_env("TEST_TIMEOUT_MULTIPLIER", 1.0)

# Specific timeout values (all affected by multiplier)
FILE_WAIT_TIMEOUT = _get_float_env("TEST_FILE_WAIT_TIMEOUT", 10.0) * TIMEOUT_MULTIPLIER
POLL_INTERVAL = _get_float_env("TEST_POLL_INTERVAL", 0.1)
SUBPROCESS_TIMEOUT = _get_int_env("TEST_SUBPROCESS_TIMEOUT", 120)
THREAD_JOIN_TIMEOUT = _get_float_env("TEST_THREAD_JOIN_TIMEOUT", 10.0) * TIMEOUT_MULTIPLIER
LOCK_TIMEOUT = _get_float_env("TEST_LOCK_TIMEOUT", 2.0) * TIMEOUT_MULTIPLIER
PROCESS_WAIT_TIMEOUT = _get_float_env("TEST_PROCESS_WAIT_TIMEOUT", 10.0) * TIMEOUT_MULTIPLIER

# Short sleeps for coordination (e.g., ensuring background task starts)
SHORT_SLEEP = _get_float_env("TEST_SHORT_SLEEP", 0.05) * TIMEOUT_MULTIPLIER
MEDIUM_SLEEP = _get_float_env("TEST_MEDIUM_SLEEP", 0.2) * TIMEOUT_MULTIPLIER


def wait_for_file(
    path: Path,
    timeout: float | None = None,
    poll_interval: float | None = None,
) -> bool:
    """Wait for a file to exist with configurable timeout.

    Args:
        path: Path to file to wait for
        timeout: Maximum time to wait (default: FILE_WAIT_TIMEOUT)
        poll_interval: How often to check (default: POLL_INTERVAL)

    Returns:
        True if file exists within timeout, False otherwise
    """
    timeout = timeout if timeout is not None else FILE_WAIT_TIMEOUT
    poll_interval = poll_interval if poll_interval is not None else POLL_INTERVAL

    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(poll_interval)
    return path.exists()


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float | None = None,
    poll_interval: float | None = None,
    error_msg: str = "Condition not met within timeout",
) -> bool:
    """Wait for a condition to be true with configurable timeout.

    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait (default: FILE_WAIT_TIMEOUT)
        poll_interval: How often to check (default: POLL_INTERVAL)
        error_msg: Error message if timeout occurs

    Returns:
        True if condition met within timeout, False otherwise
    """
    timeout = timeout if timeout is not None else FILE_WAIT_TIMEOUT
    poll_interval = poll_interval if poll_interval is not None else POLL_INTERVAL

    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(poll_interval)
    return condition()


def short_sleep() -> None:
    """Sleep for a short configurable duration.

    Use for coordination between threads/processes to ensure
    background tasks have started.
    """
    time.sleep(SHORT_SLEEP)


def medium_sleep() -> None:
    """Sleep for a medium configurable duration.

    Use when waiting for async operations to settle.
    """
    time.sleep(MEDIUM_SLEEP)
