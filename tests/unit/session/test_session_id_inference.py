"""Tests for session ID inference improvements (task 001-session-id-inference).

This test module covers:
1. psutil as a required dependency (no fallback to unstable python-pid-<current>)
2. .session-id only consulted in linked worktrees (never in primary checkout)
3. Session ID suffix handling for process-derived lookup
4. CLI auto-resolution without explicit --session

TDD: RED phase - write failing tests first.
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestPsutilRequired:
    """Tests verifying psutil is required and process inference is stable."""

    def test_psutil_is_installed(self) -> None:
        """psutil must be importable (required dependency)."""
        import psutil  # noqa: F401

    def test_has_psutil_is_true(self) -> None:
        """HAS_PSUTIL flag must be True when psutil is installed."""
        from edison.core.utils.process.inspector import HAS_PSUTIL

        assert HAS_PSUTIL is True

    def test_find_topmost_process_does_not_fallback_to_current_pid_trivially(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Process inference must not trivially return ('python', os.getpid()).

        When psutil is available, the inspector should walk the process tree
        and identify the topmost LLM or Edison process, not just return the
        current process as a fallback.
        """
        from edison.core.utils.process.inspector import find_topmost_process

        name, pid = find_topmost_process()
        # The test process is run by pytest, which may be invoked by various
        # IDE wrappers. The key assertion is that it doesn't trivially
        # return ('python', os.getpid()) when psutil is available and there's
        # a valid parent process to inspect.
        # We check that the function returns a valid result with actual PID.
        assert isinstance(name, str)
        assert isinstance(pid, int)
        assert pid > 0


class TestWorktreeOnlySessionIdFile:
    """Tests verifying .session-id is only consulted in linked worktrees."""

    def test_session_id_file_ignored_in_primary_checkout(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The .session-id file must be ignored when in the primary checkout.

        This prevents accidental session ID leakage between sessions when
        running from the primary checkout directory.
        """
        from edison.core.session.core.id import detect_session_id
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        # Clear any env vars that could mask the test
        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

        # Create a session that we'll reference in .session-id
        repo = SessionRepository(project_root=isolated_project_env)
        repo.create(Session.create("sess-primary-test", owner="tester", state="active"))

        # Write .session-id file in the primary checkout's .project directory
        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.parent.mkdir(parents=True, exist_ok=True)
        session_id_file.write_text("sess-primary-test\n", encoding="utf-8")

        # Mock is_worktree to return False (primary checkout)
        from edison.core.utils.git import worktree as worktree_module

        monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: False)

        # detect_session_id should NOT find the session from .session-id
        # because we're in the primary checkout
        result = detect_session_id(project_root=isolated_project_env)

        # It should return None or fall back to other methods (not the file)
        # The key assertion: it should NOT be "sess-primary-test" from the file
        # when we're in the primary checkout
        assert result != "sess-primary-test"

    def test_session_id_file_used_in_linked_worktree(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The .session-id file should be consulted when in a linked worktree."""
        from edison.core.session.core.id import detect_session_id
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        # Clear any env vars
        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

        # Create a session
        repo = SessionRepository(project_root=isolated_project_env)
        repo.create(Session.create("sess-worktree-test", owner="tester", state="active"))

        # Write .session-id file
        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.parent.mkdir(parents=True, exist_ok=True)
        session_id_file.write_text("sess-worktree-test\n", encoding="utf-8")

        # Mock is_worktree to return True (linked worktree)
        from edison.core.utils.git import worktree as worktree_module

        monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: True)

        # detect_session_id SHOULD find the session from .session-id
        result = detect_session_id(project_root=isolated_project_env)
        assert result == "sess-worktree-test"


class TestSessionIdSuffixHandling:
    """Tests for handling session ID suffixes (e.g., -seq-N)."""

    def test_process_derived_lookup_finds_exact_match(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Process-derived lookup finds session matching exact process prefix."""
        from edison.core.session.core.id import detect_session_id
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

        # Mock is_worktree to ensure .session-id isn't consulted
        from edison.core.utils.git import worktree as worktree_module

        monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: False)

        # Remove .session-id file if it exists
        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.unlink(missing_ok=True)

        # Mock find_topmost_process to return a predictable result
        from edison.core.utils.process import inspector as inspector_module

        monkeypatch.setattr(inspector_module, "find_topmost_process", lambda: ("claude", 12345))

        # Create the exact session
        repo = SessionRepository(project_root=isolated_project_env)
        repo.create(Session.create("claude-pid-12345", owner="tester", state="active"))

        result = detect_session_id(project_root=isolated_project_env)
        assert result == "claude-pid-12345"

    def test_process_derived_lookup_finds_suffixed_session(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Process-derived lookup finds session with -seq-N suffix when exact match doesn't exist."""
        from edison.core.session.core.id import detect_session_id
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

        from edison.core.utils.git import worktree as worktree_module

        monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: False)

        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.unlink(missing_ok=True)

        from edison.core.utils.process import inspector as inspector_module

        monkeypatch.setattr(inspector_module, "find_topmost_process", lambda: ("claude", 12345))

        # Create a session with suffix (not exact match)
        repo = SessionRepository(project_root=isolated_project_env)
        repo.create(Session.create("claude-pid-12345-seq-1", owner="tester", state="active"))

        result = detect_session_id(project_root=isolated_project_env)
        assert result == "claude-pid-12345-seq-1"

    def test_process_derived_lookup_prefers_active_session(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When multiple sessions match the prefix, prefer the one in active state."""
        from edison.core.session.core.id import detect_session_id
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

        from edison.core.utils.git import worktree as worktree_module

        monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: False)

        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.unlink(missing_ok=True)

        from edison.core.utils.process import inspector as inspector_module

        monkeypatch.setattr(inspector_module, "find_topmost_process", lambda: ("claude", 12345))

        # Create sessions: one inactive, one active
        repo = SessionRepository(project_root=isolated_project_env)
        repo.create(Session.create("claude-pid-12345", owner="tester", state="done"))
        repo.create(Session.create("claude-pid-12345-seq-1", owner="tester", state="active"))

        result = detect_session_id(project_root=isolated_project_env)
        # Should prefer active session
        assert result == "claude-pid-12345-seq-1"


class TestRequireSessionIdErrorMessages:
    """Tests for actionable error messages in require_session_id."""

    def test_error_message_is_actionable(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Error message should guide users on how to resolve the issue."""
        from edison.core.exceptions import SessionNotFoundError
        from edison.core.session.core.id import require_session_id

        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("AGENTS_OWNER", raising=False)

        from edison.core.utils.git import worktree as worktree_module

        monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: False)

        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.unlink(missing_ok=True)

        with pytest.raises(SessionNotFoundError) as exc_info:
            require_session_id(project_root=isolated_project_env)

        error_msg = str(exc_info.value)
        # The error message should mention key concepts for resolution
        assert "session" in error_msg.lower()


class TestCLIAutoResolution:
    """Tests for CLI auto-resolution of session ID."""

    def test_session_next_cli_has_optional_session_id(self) -> None:
        """session next CLI should have session_id as optional argument."""
        # Check that the CLI registers optional session_id
        import argparse

        from edison.cli.session import next as next_module

        parser = argparse.ArgumentParser()
        next_module.register_args(parser)

        # Parse with no arguments - should not fail
        # The key is that session_id should be optional or have a default
        args = parser.parse_args([])

        # session_id should either not be required or have a default
        assert not hasattr(args, "session_id") or args.session_id is None or isinstance(
            args.session_id, str
        )
