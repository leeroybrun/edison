"""Tests for `edison session cleanup-stale` CLI command.

This command provides explicit, destructive cleanup of stale sessions:
1. Restores records to global queues
2. Transitions sessions to closing state

It replaces (and provides backward compat alias for) cleanup-expired.
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
class TestSessionCleanupStale:
    """Tests for `edison session cleanup-stale` command."""

    def test_cleanup_stale_cleans_stale_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cleanup-stale should clean up sessions that are stale."""
        session_id = "sess-cleanup-stale-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.cli.session.cleanup_stale import main as cleanup_main

        args = argparse.Namespace(
            dry_run=False,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = cleanup_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert session_id in payload["cleaned"]

    def test_cleanup_stale_dry_run_does_not_modify(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cleanup-stale --dry-run should NOT modify sessions."""
        session_id = "sess-cleanup-dry-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.core.session.persistence.repository import SessionRepository

        repo = SessionRepository(project_root=isolated_project_env)

        from edison.cli.session.cleanup_stale import main as cleanup_main

        args = argparse.Namespace(
            dry_run=True,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = cleanup_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["dry_run"] is True
        assert session_id in payload["stale"]

        # Session should still be in active state
        reset_edison_caches()
        session_after = repo.get(session_id)
        assert session_after is not None
        assert session_after.state == "active"

    def test_cleanup_stale_skips_recently_active_sessions(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cleanup-stale should NOT clean recently active sessions."""
        session_id = "sess-cleanup-active-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        from edison.cli.session.cleanup_stale import main as cleanup_main

        args = argparse.Namespace(
            dry_run=False,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = cleanup_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        # Recently created session should NOT be cleaned
        assert session_id not in payload.get("cleaned", [])

    def test_cleanup_stale_uses_stale_terminology(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Human output should use 'stale' terminology."""
        session_id = "sess-cleanup-term-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.cli.session.cleanup_stale import main as cleanup_main

        args = argparse.Namespace(
            dry_run=False,
            json=False,
            repo_root=isolated_project_env,
        )
        rc = cleanup_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        assert "stale" in out.lower()


@pytest.mark.session
class TestCleanupStaleBackwardCompat:
    """Tests for backward compatibility with cleanup-expired."""

    def test_cleanup_expired_alias_works(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The existing cleanup_expired command should still work."""
        session_id = "sess-cleanup-compat-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        # Use the existing cleanup_expired command
        from edison.cli.session.cleanup_expired import main as cleanup_expired_main

        args = argparse.Namespace(
            dry_run=False,
            json=True,
        )
        rc = cleanup_expired_main(args)
        assert rc == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert session_id in payload["cleaned"]


@pytest.mark.session
class TestCleanupStaleRecordRestore:
    """Tests for record restoration during cleanup."""

    def test_cleanup_stale_restores_records_to_global(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cleanup-stale should restore session-scoped records to global queues."""
        session_id = "sess-cleanup-restore-001"
        _ensure_session_in_project(session_id, isolated_project_env, state="active")

        _make_session_stale(session_id, isolated_project_env, hours_ago=10)

        from edison.cli.session.cleanup_stale import main as cleanup_main

        args = argparse.Namespace(
            dry_run=False,
            json=True,
            repo_root=isolated_project_env,
        )
        rc = cleanup_main(args)
        assert rc == 0

        # The cleanup function should have attempted record restoration
        # (actual restoration tested in recovery module tests)
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert "cleaned" in payload
