"""
Tests for process tree inspection and PID-based session ID inference.

IMPORTANT: These tests use REAL psutil calls (NO MOCKS).
"""

import os
import pytest
from pathlib import Path

from edison.core.process.inspector import (
    find_topmost_process,
    infer_session_id,
    is_process_alive,
    _is_edison_script,
    _load_llm_process_names,
    _load_edison_process_names,
)


class TestProcessAlive:
    """Test is_process_alive() function."""

    def test_current_process_is_alive(self):
        """Current process should always be alive."""
        assert is_process_alive(os.getpid())

    def test_pid_1_usually_alive(self):
        """PID 1 (init) is usually alive on Unix systems."""
        # Skip on Windows
        if os.name != 'nt':
            assert is_process_alive(1)

    def test_nonexistent_pid_not_alive(self):
        """High PID that doesn't exist should not be alive."""
        # Use a very high PID that's unlikely to exist
        assert not is_process_alive(999999)


class TestEdisonScriptDetection:
    """Test _is_edison_script() helper."""

    def test_detects_edison_in_cmdline(self):
        """Should detect 'edison' in command line."""
        cmdline = ["python", "/path/to/edison", "session", "start"]
        assert _is_edison_script(cmdline)

    def test_detects_dotedison_in_cmdline(self):
        """Should detect '.edison' in command line."""
        cmdline = ["python", "/project/src/edison/core/tasks/manager.py"]
        assert _is_edison_script(cmdline)

    def test_detects_scripts_tasks(self):
        """Should detect 'edison' package in command line."""
        cmdline = ["python", "-m", "edison.core.task.claims", "TASK-123"]
        assert _is_edison_script(cmdline)

    def test_rejects_non_edison_cmdline(self):
        """Should reject non-Edison command lines."""
        cmdline = ["python", "/usr/local/bin/myapp.py"]
        assert not _is_edison_script(cmdline)


class TestFindTopmostProcess:
    """Test find_topmost_process() function."""

    def test_returns_valid_tuple(self):
        """Should return (name, pid) tuple."""
        name, pid = find_topmost_process()
        assert isinstance(name, str)
        assert isinstance(pid, int)
        assert pid > 0

    def test_returns_known_process_name(self):
        """Should return a known process name."""
        name, pid = find_topmost_process()
        llm_names = _load_llm_process_names()
        edison_names = _load_edison_process_names()
        valid_names = llm_names + edison_names + ["python"]
        assert name in valid_names

    def test_pid_is_alive(self):
        """Returned PID should be alive."""
        name, pid = find_topmost_process()
        assert is_process_alive(pid)


class TestInferSessionId:
    """Test infer_session_id() function."""

    def test_format_is_correct(self):
        """Session ID should match {name}-pid-{pid} format."""
        session_id = infer_session_id()
        assert session_id.count("-pid-") == 1
        parts = session_id.split("-pid-")
        assert len(parts) == 2
        name, pid_str = parts
        assert len(name) > 0
        assert pid_str.isdigit()

    def test_pid_is_valid(self):
        """PID in session ID should be valid and alive."""
        session_id = infer_session_id()
        pid_str = session_id.split("-pid-")[1]
        pid = int(pid_str)
        assert pid > 0
        assert is_process_alive(pid)

    def test_consistent_within_same_process(self):
        """Multiple calls should return same session ID."""
        id1 = infer_session_id()
        id2 = infer_session_id()
        assert id1 == id2

    def test_filesystem_safe(self):
        """Session ID should be filesystem-safe."""
        session_id = infer_session_id()
        # No path traversal characters
        assert ".." not in session_id
        assert "/" not in session_id
        assert "\\" not in session_id
        # No special characters that break directories
        assert all(c.isalnum() or c in ["-", "_"] for c in session_id)


class TestConfiguration:
    """Test configuration loading."""

    def test_load_llm_names_returns_list(self):
        """Should return list of LLM process names."""
        names = _load_llm_process_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert "claude" in names
        assert "codex" in names

    def test_load_edison_names_returns_list(self):
        """Should return list of Edison process names."""
        names = _load_edison_process_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert "edison" in names or "python" in names
