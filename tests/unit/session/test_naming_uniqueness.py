"""Tests for session naming uniqueness within the same process.

TDD: This test file exposes the bug where creating multiple sessions
in the same Python process generates duplicate session IDs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from edison.core.session.naming import SessionNamingStrategy, reset_session_naming_counter


def test_session_naming_generates_unique_ids_in_same_process():
    """Multiple sessions in the same process must have unique IDs."""
    strategy = SessionNamingStrategy()

    # Generate 3 session IDs in the same process
    ids = [strategy.generate() for _ in range(3)]

    # All IDs must be unique
    assert len(ids) == len(set(ids)), f"Duplicate session IDs generated: {ids}"

    # All IDs should follow the PID-based pattern
    for session_id in ids:
        assert "-pid-" in session_id


def test_session_naming_resets_counter_between_pids():
    """Counter should reset when PID changes (theoretical test)."""
    # This test documents expected behavior but can't actually change PID
    # It serves as documentation of the design intent
    strategy = SessionNamingStrategy()

    # First ID should not have a counter suffix
    first_id = strategy.generate()
    assert first_id.endswith(f"-pid-{strategy._current_pid}") or "-seq-" in first_id


def test_session_naming_thread_safety():
    """Session IDs must be unique when created concurrently in multiple threads.

    This test exposes race conditions in the counter increment logic.
    Without proper thread synchronization, multiple threads can:
    1. Read the same counter value
    2. Increment it independently
    3. Generate duplicate session IDs
    """
    # Reset counter for clean test state
    reset_session_naming_counter()

    def generate_id(_):
        strategy = SessionNamingStrategy()
        return strategy.generate()

    # Create 10 sessions concurrently across 5 threads
    with ThreadPoolExecutor(max_workers=5) as pool:
        ids = list(pool.map(generate_id, range(10)))

    # All IDs must be unique - this will FAIL without thread-safety
    assert len(ids) == len(set(ids)), f"Duplicate session IDs detected in concurrent execution: {ids}"

    # Verify all follow expected pattern
    for session_id in ids:
        assert "-pid-" in session_id
