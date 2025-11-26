"""
Tests for PID-based session naming.

WAVE 1-4 used timestamp-based naming (DEPRECATED).
WAVE 5 uses PID-based naming via process tree inspection.

Note: Session IDs now include a sequence number for uniqueness when
multiple sessions are created in the same process (e.g., python-pid-123-seq-1).
"""

import pytest

from edison.core.session.naming import (
    SessionNamingStrategy,
    SessionNamingError,
    reset_session_naming_counter,
)
from edison.core.process.inspector import infer_session_id


@pytest.fixture(autouse=True)
def reset_naming_counter():
    """Reset the session naming counter before each test."""
    reset_session_naming_counter()
    yield
    reset_session_naming_counter()


class TestSessionNamingStrategy:
    """Test PID-based session naming strategy."""

    def test_naming_strategy_uses_pid(self):
        """Should use PID-based inference."""
        naming = SessionNamingStrategy()
        session_id = naming.generate()

        assert "-pid-" in session_id

    def test_naming_format(self):
        """Should match {name}-pid-{pid} format for first session."""
        naming = SessionNamingStrategy()
        session_id = naming.generate()

        # First session has no sequence suffix
        parts = session_id.split("-pid-")
        assert len(parts) == 2
        name, pid_str = parts
        assert len(name) > 0
        assert pid_str.isdigit()

    def test_naming_uniqueness_with_sequence(self):
        """Multiple sessions should have unique IDs via sequence numbers."""
        naming = SessionNamingStrategy()
        id1 = naming.generate()
        id2 = naming.generate()
        id3 = naming.generate()

        # First session has no suffix
        assert "-seq-" not in id1
        # Subsequent sessions have sequence suffixes
        assert "-seq-1" in id2
        assert "-seq-2" in id3

        # All IDs are unique
        assert len({id1, id2, id3}) == 3

    def test_naming_base_matches_infer_session_id(self):
        """First session should match direct call to infer_session_id()."""
        naming = SessionNamingStrategy()
        from_naming = naming.generate()
        from_inspector = infer_session_id()

        assert from_naming == from_inspector

    def test_naming_ignores_process_arg(self):
        """Process arg should be ignored (deprecated)."""
        naming = SessionNamingStrategy()
        id_without_arg = naming.generate()
        reset_session_naming_counter()  # Reset to get same sequence
        id_with_arg = naming.generate(process="TASK-123")

        # Both should be first session (no seq suffix)
        assert "-seq-" not in id_without_arg
        assert "-seq-" not in id_with_arg
        assert "-pid-" in id_with_arg

    def test_naming_ignores_owner_arg(self):
        """Owner arg should be ignored (deprecated)."""
        naming = SessionNamingStrategy()
        id_without_owner = naming.generate()
        reset_session_naming_counter()  # Reset to get same sequence
        id_with_owner = naming.generate(owner="claude")

        assert id_with_owner == id_without_owner

    def test_naming_ignores_existing_sessions_arg(self):
        """Existing sessions arg should be ignored (no collision check needed)."""
        naming = SessionNamingStrategy()
        id_without_existing = naming.generate()
        reset_session_naming_counter()  # Reset to get same sequence
        id_with_existing = naming.generate(existing_sessions=["old-1", "old-2"])

        assert id_with_existing == id_without_existing

    def test_validate_pid_format(self):
        """Should validate PID-based session IDs."""
        naming = SessionNamingStrategy()
        session_id = naming.generate()

        assert naming.validate(session_id)

    def test_validate_rejects_path_traversal(self):
        """Should reject path traversal attempts."""
        naming = SessionNamingStrategy()

        assert not naming.validate("../../../etc/passwd")
        assert not naming.validate("session/../hack")

    def test_validate_rejects_special_chars(self):
        """Should reject special characters."""
        naming = SessionNamingStrategy()

        assert not naming.validate("session;rm -rf")
        assert not naming.validate("session|evil")
        assert not naming.validate("session&backdoor")

    def test_filesystem_safe(self):
        """Generated IDs should be filesystem-safe."""
        naming = SessionNamingStrategy()
        session_id = naming.generate()

        assert "/" not in session_id
        assert "\\" not in session_id
        assert ".." not in session_id
        assert all(c.isalnum() or c in ["-", "_"] for c in session_id)


class TestBackwardCompatibility:
    """Test backward compatibility with WAVE 1-4 code."""

    def test_accepts_config_arg(self):
        """Should accept config arg (but ignore it)."""
        config = {"strategy": "edison", "template": "old-{timestamp}"}
        naming = SessionNamingStrategy(config)

        session_id = naming.generate()
        assert "-pid-" in session_id

    def test_accepts_kwargs(self):
        """Should accept arbitrary kwargs (but ignore them)."""
        naming = SessionNamingStrategy()

        session_id = naming.generate(
            process="TASK-123",
            owner="claude",
            naming_strategy="custom",
            template="{process}-{shortid}",
        )

        assert "-pid-" in session_id


class TestErrorHandling:
    """Test error handling."""

    def test_raises_on_inspector_failure(self, monkeypatch):
        """Should raise SessionNamingError if inspector fails."""
        from edison.core.process import inspector

        def broken_find():
            raise RuntimeError("Process inspection failed")

        monkeypatch.setattr(inspector, "find_topmost_process", broken_find)

        naming = SessionNamingStrategy()
        with pytest.raises(SessionNamingError):
            naming.generate()

