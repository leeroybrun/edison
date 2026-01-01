"""Tests for `edison session stale` CLI command.

This command lists sessions that are stale (inactive beyond the configured timeout),
but remain resumable. It replaces the "expired" terminology with "stale due to inactivity".
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.helpers.cache_utils import reset_edison_caches


def _ensure_session_in_project(session_id: str, project_root: Path, state: str = "active") -> Path:
    """Create a session in the given project root.

    Unlike the global ensure_session helper, this explicitly uses the provided
    project_root to avoid PathResolver cache issues in isolated test environments.
    """
    from edison.core.session.persistence.repository import SessionRepository

    reset_edison_caches()
    repo = SessionRepository(project_root=project_root)
    return repo.ensure_session(session_id, state=state)


def _make_session_stale(session_id: str, project_root: Path, hours_ago: int = 10) -> None:
    """Helper to backdate session timestamps to make it stale.

    Note: We must write directly to the JSON file rather than using repo.save()
    because save() calls metadata.touch() which updates lastActive to now.

    IMPORTANT: We must backdate BOTH lastActive AND createdAt because
    _effective_activity_time() returns max(lastActive, claimed, createdAt).
    If only lastActive is backdated but createdAt is recent, the session
    won't be considered stale.
    """
    import json as json_mod
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.io import write_json_atomic

    repo = SessionRepository(project_root=project_root)
    session_path = repo._find_entity_path(session_id)
    assert session_path is not None and session_path.exists()

    # Read current session data
    data = json_mod.loads(session_path.read_text(encoding="utf-8"))

    # Backdate BOTH lastActive AND createdAt timestamps
    old_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    old_time_iso = old_time.isoformat()
    if "meta" not in data:
        data["meta"] = {}
    data["meta"]["lastActive"] = old_time_iso
    data["meta"]["createdAt"] = old_time_iso

    # Write directly without going through repo.save (which calls touch())
    write_json_atomic(session_path, data, acquire_lock=False)
    reset_edison_caches()


@pytest.mark.session
class TestSessionStaleList:
    """Tests for `edison session stale --list` command."""

    def test_stale_list_returns_empty_when_no_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When no sessions exist, stale --list should return empty list."""
        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=True,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["stale_sessions"] == []
        assert payload["count"] == 0

    def test_stale_list_excludes_active_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Active sessions (recently active) should NOT appear in stale list."""
        session_id = "sess-stale-active-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=True,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        # Session was just created, should NOT be stale
        stale_ids = [s["id"] for s in payload["stale_sessions"]]
        assert session_id not in stale_ids

    def test_stale_list_includes_stale_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Sessions that exceeded inactivity timeout should appear in stale list."""
        session_id = "sess-stale-old-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        # Make the session stale (default timeout is 8 hours)
        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=True,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        stale_ids = [s["id"] for s in payload["stale_sessions"]]
        assert session_id in stale_ids

    def test_stale_list_text_output_uses_stale_terminology(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Human output should use 'stale' terminology, not 'expired'."""
        session_id = "sess-stale-text-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=True,
            json=False,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        # Should use "stale" terminology
        assert "stale" in out.lower()
        assert session_id in out

    def test_stale_list_shows_inactivity_duration(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Stale list should show how long each session has been inactive."""
        session_id = "sess-stale-duration-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=12)

        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=True,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["count"] >= 1

        stale_session = next(
            (s for s in payload["stale_sessions"] if s["id"] == session_id), None
        )
        assert stale_session is not None
        # Should have inactivity duration info
        assert "inactiveHours" in stale_session or "lastActive" in stale_session


@pytest.mark.session
class TestSessionStaleNonDestructive:
    """Verify that `edison session stale --list` is non-destructive."""

    def test_stale_list_does_not_modify_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Running stale --list should NOT modify session state."""
        session_id = "sess-stale-readonly-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.core.session.persistence.repository import SessionRepository

        repo = SessionRepository(project_root=isolated_project_env)

        # Get session state before
        session_before = repo.get(session_id)
        assert session_before is not None
        state_before = session_before.state

        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=True,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        assert rc == 0

        # Session state should be unchanged
        reset_edison_caches()
        session_after = repo.get(session_id)
        assert session_after is not None
        assert session_after.state == state_before


@pytest.mark.session
class TestSessionStaleRequiresListFlag:
    """Tests verifying --list flag is required."""

    def test_stale_without_list_flag_shows_help(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Running 'session stale' without --list should show usage."""
        from edison.cli.session.stale import main as stale_main

        args = argparse.Namespace(
            list=False,
            json=False,
            repo_root=isolated_project_env,
        )
        rc = stale_main(args)
        # Should succeed but indicate no action taken or show help
        assert rc in (0, 1)

        out = capsys.readouterr()
        # Either shows help text or indicates --list is needed
        combined = out.out + out.err
        assert "--list" in combined or "stale" in combined.lower()
