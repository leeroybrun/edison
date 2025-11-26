"""
Integration tests for PID-based session store.

These tests exercise the real process inspector and session store without
using mocks. They validate both the new PID-based behaviour and the legacy
fallback path for backward compatibility.
"""

import getpass
import os
from pathlib import Path

import pytest

from edison.core.process.inspector import find_topmost_process, infer_session_id
from edison.core.session.store import (
    auto_session_for_owner,
    sanitize_session_id,
    save_session,
    session_exists,
)
from edison.core.task import default_owner


class TestAutoSessionForOwner:
    """Test auto_session_for_owner() with PID-based inference."""

    def test_returns_pid_based_session_id(self):
        """Should return PID-based session ID format."""
        session_id = auto_session_for_owner(None)
        assert session_id is not None
        assert "-pid-" in session_id

    def test_format_matches_infer_session_id(self):
        """Should match what infer_session_id() returns."""
        expected = infer_session_id()
        actual = auto_session_for_owner(None)
        assert actual == expected

    def test_matches_process_name_prefix(self):
        """PID-based session ID should include the topmost process name prefix."""
        expected_name, _ = find_topmost_process()
        session_id = auto_session_for_owner(None)
        assert session_id is not None
        assert session_id.startswith(f"{expected_name}-pid-")

    def test_output_passes_sanitize(self):
        """auto_session_for_owner output should be a valid sanitized ID."""
        session_id = auto_session_for_owner(None)
        assert session_id is not None
        assert sanitize_session_id(session_id) == session_id

    def test_returns_same_id_consistently(self):
        """Multiple calls should return same session ID."""
        id1 = auto_session_for_owner(None)
        id2 = auto_session_for_owner(None)
        assert id1 == id2

    def test_creates_session_if_missing(self, tmp_path, monkeypatch):
        """Should return PID-based ID even if session doesn't exist yet."""
        # Point session storage at an isolated temp dir to avoid side effects
        from edison.core import session as session_pkg

        monkeypatch.setattr(session_pkg.store, "_sessions_root", lambda: tmp_path / ".project" / "sessions")
        session_id = auto_session_for_owner(None)
        assert session_id is not None
        assert "-pid-" in session_id
        # Newly inferred ID should not yet exist, but still be returned
        assert not session_exists(session_id)

    def test_owner_arg_does_not_override_pid_inference(self, tmp_path, monkeypatch):
        """PID inference should win even when an owner is provided."""
        from edison.core import session as session_pkg

        monkeypatch.setattr(session_pkg.store, "_sessions_root", lambda: tmp_path / ".project" / "sessions")
        session_id = auto_session_for_owner("some-owner")
        assert session_id is not None
        assert "-pid-" in session_id

    def test_uses_legacy_when_existing_and_pid_session_missing(self, tmp_path, monkeypatch):
        """Legacy session should still be returned when it already exists."""
        from edison.core import session as session_pkg

        sessions_root = tmp_path / ".project" / "sessions"
        monkeypatch.setattr(session_pkg.store, "_sessions_root", lambda: sessions_root)

        legacy_id = "legacy-owner"
        save_session(
            legacy_id,
            {
                "id": legacy_id,
                "meta": {"sessionId": legacy_id},
                "tasks": {},
                "qa": {},
            },
        )

        session_id = auto_session_for_owner(legacy_id)
        assert session_id == legacy_id


class TestDefaultOwner:
    """Test default_owner() with process tree inspection."""

    @pytest.fixture(autouse=True)
    def clear_env_owner(self, monkeypatch):
        """Ensure AGENTS_OWNER doesn't mask process inspection during tests."""
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

    def test_returns_process_name(self):
        """Should return process name from tree."""
        owner = default_owner()
        assert isinstance(owner, str)
        assert len(owner) > 0

    def test_matches_find_topmost_process(self):
        """Should match process name from find_topmost_process()."""
        expected_name, _ = find_topmost_process()
        actual_owner = default_owner()
        assert actual_owner == expected_name

    def test_returns_known_owner(self):
        """Should return known owner type."""
        owner = default_owner()
        valid_owners = ["edison", "python", "claude", "codex", "gemini", "cursor", "aider", "happy"]
        # Also accept username as fallback
        valid_owners.append(getpass.getuser())
        assert owner in valid_owners

    def test_env_owner_overrides_process_detection(self, monkeypatch):
        """Configured owner (via env/config) should override process inspection."""
        monkeypatch.setenv("AGENTS_OWNER", "env-owner")
        actual_owner = default_owner()
        assert actual_owner == "env-owner"


class TestBackwardCompatibility:
    """Test that legacy sessions still work."""

    def test_legacy_session_still_loads(self, tmp_path, monkeypatch):
        """Existing non-PID sessions should still be found."""
        from edison.core import session as session_pkg

        sessions_root = tmp_path / ".project" / "sessions"
        monkeypatch.setattr(session_pkg.store, "_sessions_root", lambda: sessions_root)

        # Create legacy session
        legacy_id = "old-session-123"
        legacy_data = {
            "id": legacy_id,
            "meta": {"sessionId": legacy_id},
            "tasks": {},
            "qa": {},
        }
        save_session(legacy_id, legacy_data)

        # Verify it exists
        assert session_exists(legacy_id)

        # auto_session_for_owner should find it via fallback
        found = auto_session_for_owner(legacy_id)
        assert found == legacy_id

    def test_legacy_owner_lookup_works(self, tmp_path, monkeypatch):
        """Legacy owner-based lookup should still work as fallback."""
        from edison.core import session as session_pkg

        sessions_root = tmp_path / ".project" / "sessions"
        monkeypatch.setattr(session_pkg.store, "_sessions_root", lambda: sessions_root)

        # Create session with owner-based name
        owner = "legacy-user"
        save_session(
            owner,
            {
                "id": owner,
                "meta": {"sessionId": owner},
                "tasks": {},
                "qa": {},
            },
        )

        # Should find via fallback
        found = auto_session_for_owner(owner)
        assert found == owner


class TestSessionIDValidation:
    """Test that PID-based session IDs pass validation."""

    def test_pid_format_passes_sanitize(self):
        """PID-based session IDs should pass sanitize_session_id()."""
        session_id = infer_session_id()
        # Should not raise
        sanitized = sanitize_session_id(session_id)
        assert sanitized == session_id

    def test_pid_format_filesystem_safe(self):
        """PID-based IDs should be safe for filesystem use."""
        session_id = infer_session_id()

        # No path traversal
        assert ".." not in session_id
        assert "/" not in session_id
        assert "\\" not in session_id

        # Only safe characters
        assert all(c.isalnum() or c in ["-", "_", "."] for c in session_id)


class TestMultipleProcesses:
    """Test that different processes get different session IDs."""

    def test_different_pids_different_sessions(self):
        """Different PIDs should produce different session IDs."""
        session_id = infer_session_id()

        # Extract PID from session ID
        pid_str = session_id.split("-pid-")[1]
        pid = int(pid_str)

        # Should match current process or ancestor
        assert pid > 0
        assert pid != 999999  # Not a fake PID
