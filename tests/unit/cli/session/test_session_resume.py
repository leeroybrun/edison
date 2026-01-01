"""Tests for `edison session resume` CLI command.

This command helps resume a session by:
1. Validating the session exists
2. Printing `export AGENTS_SESSION=<id>` guidance
3. In worktrees, optionally setting .session-id file
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.helpers.session import ensure_session
from tests.helpers.cache_utils import reset_edison_caches


@pytest.mark.session
class TestSessionResumeValidation:
    """Tests for session validation in resume command."""

    def test_resume_validates_session_exists(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resume should fail if session does not exist."""
        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id="nonexistent-session-001",
            json=False,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc != 0

        out = capsys.readouterr()
        combined = out.out + out.err
        assert "not found" in combined.lower() or "error" in combined.lower()

    def test_resume_succeeds_for_existing_session(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resume should succeed for an existing session."""
        session_id = "sess-resume-exists-001"
        ensure_session(session_id, state="active")

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=False,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc == 0


@pytest.mark.session
class TestSessionResumeEnvGuidance:
    """Tests for environment variable guidance in resume command."""

    def test_resume_prints_export_guidance(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resume should print `export AGENTS_SESSION=<id>` guidance."""
        session_id = "sess-resume-export-001"
        ensure_session(session_id, state="active")

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=False,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        assert "export AGENTS_SESSION=" in out
        assert session_id in out

    def test_resume_json_includes_export_command(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output should include the export command."""
        session_id = "sess-resume-json-001"
        ensure_session(session_id, state="active")

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=True,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["session_id"] == session_id
        assert "exportCommand" in payload
        assert session_id in payload["exportCommand"]


@pytest.mark.session
class TestSessionResumeSessionIdFile:
    """Tests for .session-id file handling in resume command."""

    def test_resume_with_set_file_in_worktree(
        self,
        isolated_project_env: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Resume with --set-file should write .session-id in worktree."""
        session_id = "sess-resume-setfile-001"
        ensure_session(session_id, state="active")

        # Simulate being in a worktree
        from edison.core.utils.git import worktree as git_worktree_module

        monkeypatch.setattr(git_worktree_module, "is_worktree", lambda: True)

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=False,
            repo_root=isolated_project_env,
            set_file=True,
        )
        rc = resume_main(args)
        assert rc == 0

        # Check the .session-id file was created
        session_id_file = isolated_project_env / ".project" / ".session-id"
        assert session_id_file.exists()
        assert session_id_file.read_text(encoding="utf-8").strip() == session_id

    def test_resume_without_set_file_does_not_write_file(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resume without --set-file should NOT write .session-id file."""
        session_id = "sess-resume-nofile-001"
        ensure_session(session_id, state="active")

        # Remove any existing .session-id file
        session_id_file = isolated_project_env / ".project" / ".session-id"
        session_id_file.unlink(missing_ok=True)

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=False,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc == 0

        # .session-id file should NOT be created
        assert not session_id_file.exists()


@pytest.mark.session
class TestSessionResumeSessionInfo:
    """Tests for session info in resume output."""

    def test_resume_shows_session_state(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resume should show the current session state."""
        session_id = "sess-resume-state-001"
        ensure_session(session_id, state="active")

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=True,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert "state" in payload
        assert payload["state"] == "active"

    def test_resume_shows_worktree_path_if_available(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resume should show worktree path if session has one."""
        session_id = "sess-resume-wt-001"
        ensure_session(session_id, state="active")

        # Set a worktree path on the session
        from edison.core.session.persistence.repository import SessionRepository

        repo = SessionRepository(project_root=isolated_project_env)
        session = repo.get(session_id)
        assert session is not None

        session.git.worktree_path = str(isolated_project_env / ".worktrees" / "test-wt")
        repo.save(session)
        reset_edison_caches()

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=True,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert "worktreePath" in payload


@pytest.mark.session
class TestSessionResumeCanResumeStale:
    """Tests verifying stale sessions can be resumed."""

    def test_resume_works_for_stale_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Stale sessions should be resumable (not blocked)."""
        session_id = "sess-resume-stale-001"
        ensure_session(session_id, state="active")

        # Make the session stale
        from edison.core.session.persistence.repository import SessionRepository

        repo = SessionRepository(project_root=isolated_project_env)
        session = repo.get(session_id)
        assert session is not None

        old_time = datetime.now(timezone.utc) - timedelta(hours=10)
        session.metadata.updated_at = old_time.isoformat()
        repo.save(session)
        reset_edison_caches()

        from edison.cli.session.resume import main as resume_main

        args = argparse.Namespace(
            session_id=session_id,
            json=False,
            repo_root=isolated_project_env,
            set_file=False,
        )
        rc = resume_main(args)
        # Should succeed - stale sessions are resumable
        assert rc == 0
