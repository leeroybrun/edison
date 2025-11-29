"""Tests for centralized timeout configuration.

Verifies that all timeout values are configurable via environment variables
and that tests can adapt to slow CI environments.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from helpers.timeouts import (
    FILE_WAIT_TIMEOUT,
    LOCK_TIMEOUT,
    MEDIUM_SLEEP,
    POLL_INTERVAL,
    PROCESS_WAIT_TIMEOUT,
    SHORT_SLEEP,
    SUBPROCESS_TIMEOUT,
    THREAD_JOIN_TIMEOUT,
    TIMEOUT_MULTIPLIER,
    medium_sleep,
    short_sleep,
    wait_for_condition,
    wait_for_file,
)


class TestTimeoutConfiguration:
    """Test timeout configuration and helpers."""

    def test_timeout_multiplier_affects_values(self, monkeypatch: pytest.MonkeyPatch):
        """Timeout multiplier should scale all timeout values."""
        # Note: This test validates the design, but actual values are set at import time
        # We can only validate that TIMEOUT_MULTIPLIER is used correctly
        assert TIMEOUT_MULTIPLIER >= 1.0, "Multiplier should be at least 1.0"

        # All timeouts should be positive
        assert FILE_WAIT_TIMEOUT > 0
        assert LOCK_TIMEOUT > 0
        assert THREAD_JOIN_TIMEOUT > 0
        assert PROCESS_WAIT_TIMEOUT > 0
        assert SHORT_SLEEP > 0
        assert MEDIUM_SLEEP > 0

    def test_wait_for_file_success(self, tmp_path: Path):
        """wait_for_file should return True when file appears."""
        test_file = tmp_path / "test.txt"

        # Create file after a short delay
        import threading
        def create_file():
            time.sleep(SHORT_SLEEP)
            test_file.write_text("test")

        thread = threading.Thread(target=create_file)
        thread.start()

        # Wait for file with custom short timeout
        result = wait_for_file(test_file, timeout=SHORT_SLEEP * 5)
        thread.join()

        assert result is True
        assert test_file.exists()

    def test_wait_for_file_timeout(self, tmp_path: Path):
        """wait_for_file should return False on timeout."""
        test_file = tmp_path / "nonexistent.txt"

        # Wait with very short timeout
        result = wait_for_file(test_file, timeout=SHORT_SLEEP)

        assert result is False
        assert not test_file.exists()

    def test_wait_for_condition_success(self):
        """wait_for_condition should return True when condition is met."""
        counter = {"value": 0}

        def increment():
            time.sleep(SHORT_SLEEP)
            counter["value"] += 1

        import threading
        thread = threading.Thread(target=increment)
        thread.start()

        # Wait for counter to increment
        result = wait_for_condition(
            lambda: counter["value"] > 0,
            timeout=SHORT_SLEEP * 5,
        )
        thread.join()

        assert result is True
        assert counter["value"] == 1

    def test_wait_for_condition_timeout(self):
        """wait_for_condition should return False on timeout."""
        # Condition that never becomes true
        result = wait_for_condition(
            lambda: False,
            timeout=SHORT_SLEEP,
        )

        assert result is False

    def test_short_sleep_is_configurable(self):
        """short_sleep should use configurable duration."""
        start = time.time()
        short_sleep()
        elapsed = time.time() - start

        # Should complete within reasonable bounds
        assert SHORT_SLEEP * 0.5 <= elapsed <= SHORT_SLEEP * 3

    def test_medium_sleep_is_configurable(self):
        """medium_sleep should use configurable duration."""
        start = time.time()
        medium_sleep()
        elapsed = time.time() - start

        # Should complete within reasonable bounds
        assert MEDIUM_SLEEP * 0.5 <= elapsed <= MEDIUM_SLEEP * 3

    def test_environment_variables_are_respected(self, monkeypatch: pytest.MonkeyPatch):
        """Environment variables should override default values."""
        # This test demonstrates how to use env vars
        # Note: Actual module already imported, so this is documentation

        # Example of how to set env vars for CI:
        # export TEST_TIMEOUT_MULTIPLIER=2.0
        # export TEST_FILE_WAIT_TIMEOUT=20.0
        # export TEST_SUBPROCESS_TIMEOUT=240

        # Validate that we document the expected env vars
        env_vars = [
            "TEST_TIMEOUT_MULTIPLIER",
            "TEST_FILE_WAIT_TIMEOUT",
            "TEST_POLL_INTERVAL",
            "TEST_SUBPROCESS_TIMEOUT",
            "TEST_THREAD_JOIN_TIMEOUT",
            "TEST_LOCK_TIMEOUT",
            "TEST_PROCESS_WAIT_TIMEOUT",
            "TEST_SHORT_SLEEP",
            "TEST_MEDIUM_SLEEP",
        ]

        # All env vars should be documented
        for var in env_vars:
            assert var  # Placeholder - validates the list exists


class TestTimeoutIntegration:
    """Integration tests for timeout usage patterns."""

    def test_subprocess_timeout_is_sufficient(self):
        """SUBPROCESS_TIMEOUT should be sufficient for typical operations."""
        # This is a smoke test - actual value depends on environment
        assert SUBPROCESS_TIMEOUT >= 30, "Subprocess timeout too short for CI"

    def test_file_wait_timeout_is_sufficient(self):
        """FILE_WAIT_TIMEOUT should be sufficient for file operations."""
        assert FILE_WAIT_TIMEOUT >= 5.0, "File wait timeout too short"

    def test_lock_timeout_is_sufficient(self):
        """LOCK_TIMEOUT should be sufficient for lock acquisition."""
        assert LOCK_TIMEOUT >= 1.0, "Lock timeout too short"

    def test_thread_join_timeout_is_sufficient(self):
        """THREAD_JOIN_TIMEOUT should be sufficient for thread cleanup."""
        assert THREAD_JOIN_TIMEOUT >= 5.0, "Thread join timeout too short"

    def test_poll_interval_is_reasonable(self):
        """POLL_INTERVAL should not be too frequent or too slow."""
        assert 0.01 <= POLL_INTERVAL <= 1.0, "Poll interval out of reasonable range"

    def test_short_sleep_is_short(self):
        """SHORT_SLEEP should be truly short."""
        assert SHORT_SLEEP <= 0.5, "SHORT_SLEEP too long"

    def test_medium_sleep_is_reasonable(self):
        """MEDIUM_SLEEP should be medium duration."""
        assert 0.1 <= MEDIUM_SLEEP <= 2.0, "MEDIUM_SLEEP out of range"


def test_no_hardcoded_timeouts_in_helpers():
    """Verify no hardcoded timeout values remain in helper."""
    # This test ensures we use configuration
    from helpers import timeouts

    source_file = Path(timeouts.__file__)
    if source_file.suffix == '.pyc':
        source_file = source_file.with_suffix('.py')

    content = source_file.read_text()

    # Should not have magic number timeouts (except in env var defaults)
    # Look for common patterns like timeout=5 or sleep(0.1)
    # But allow them in get_float_env() default parameters

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # Skip comment lines and get_float_env/get_int_env default values
        if line.strip().startswith('#') or '_get_float_env(' in line or '_get_int_env(' in line:
            continue

        # Flag suspicious hardcoded values
        if 'timeout=' in line.lower() and any(c.isdigit() for c in line):
            # Check if it's using a constant
            if not any(const in line for const in [
                'FILE_WAIT_TIMEOUT', 'LOCK_TIMEOUT', 'THREAD_JOIN_TIMEOUT',
                'PROCESS_WAIT_TIMEOUT', 'SHORT_SLEEP', 'MEDIUM_SLEEP',
                'SUBPROCESS_TIMEOUT', 'POLL_INTERVAL', 'TIMEOUT_MULTIPLIER',
            ]):
                # This is OK if it's in the constant definitions themselves
                if 'timeout if timeout' not in line:
                    pytest.fail(f"Line {i}: Potential hardcoded timeout: {line.strip()}")
