"""Test that SessionRepository uses nested layout correctly.

This test file verifies that the SessionRepository creates session files
in the NESTED layout to match existing project conventions:
- .project/sessions/wip/{session-id}/session.json (NESTED)
- NOT .project/sessions/wip/{session-id}.json (FLAT)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from edison.core.session.repository import SessionRepository
from edison.core.session.manager import SessionManager
from edison.core.session.models import Session


@pytest.mark.session
class TestNestedSessionLayout:
    """Test that session files use nested layout."""

    def test_create_uses_nested_layout(self, tmp_path: Path):
        """Creating a session should use nested layout."""
        repo = SessionRepository(project_root=tmp_path)

        # Create session
        session = Session.create("test-nested", state="active", owner="tester")
        repo.create(session)

        # Verify nested layout
        expected_path = tmp_path / ".project" / "sessions" / "wip" / "test-nested" / "session.json"
        assert expected_path.exists(), f"Expected {expected_path} to exist"

        # Verify flat layout does NOT exist
        flat_path = tmp_path / ".project" / "sessions" / "wip" / "test-nested.json"
        assert not flat_path.exists(), f"Flat layout {flat_path} should not exist"

    def test_get_session_json_path_returns_nested_path(self, tmp_path: Path):
        """get_session_json_path should return nested layout path."""
        repo = SessionRepository(project_root=tmp_path)

        # Create session
        session = Session.create("test-path", state="active")
        repo.create(session)

        # Get path
        path = repo.get_session_json_path("test-path")

        # Verify it's nested layout
        assert path.name == "session.json"
        assert path.parent.name == "test-path"
        assert "wip" in str(path)

    def test_state_transition_moves_nested_directory(self, tmp_path: Path):
        """State transitions should move the entire nested directory."""
        repo = SessionRepository(project_root=tmp_path)

        # Create session in active state
        session = Session.create("test-transition", state="active", owner="tester")
        repo.create(session)

        active_dir = tmp_path / ".project" / "sessions" / "wip" / "test-transition"
        assert active_dir.exists()
        assert (active_dir / "session.json").exists()

        # Transition to done
        session.state = "done"
        repo.save(session)

        # Verify moved to done directory
        done_dir = tmp_path / ".project" / "sessions" / "done" / "test-transition"
        assert done_dir.exists()
        assert (done_dir / "session.json").exists()

        # Verify old location is gone
        assert not active_dir.exists()

    def test_list_by_state_with_nested_layout(self, tmp_path: Path):
        """list_by_state should work with nested layout."""
        repo = SessionRepository(project_root=tmp_path)

        # Create multiple sessions
        for i in range(3):
            session = Session.create(f"session-{i}", state="active", owner=f"owner-{i}")
            repo.create(session)

        # List sessions
        sessions = repo.list_by_state("active")

        # Verify all found
        assert len(sessions) == 3
        session_ids = {s.id for s in sessions}
        assert session_ids == {"session-0", "session-1", "session-2"}

    def test_manager_create_uses_nested_layout(self, tmp_path: Path):
        """SessionManager.create should use nested layout."""
        mgr = SessionManager(project_root=tmp_path)

        # Create session
        path = mgr.create("test-mgr", owner="manager")

        # Verify returned path is nested
        assert path.name == "session.json"
        assert path.parent.name == "test-mgr"

        # Verify file exists
        assert path.exists()

        # Verify content
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["id"] == "test-mgr"
        assert data.get("meta", {}).get("owner") == "manager"

    def test_nested_layout_supports_related_files(self, tmp_path: Path):
        """Nested layout allows storing tasks/qa alongside session.json."""
        repo = SessionRepository(project_root=tmp_path)

        # Create session
        session = Session.create("test-related", state="active")
        repo.create(session)

        # Get session directory
        session_dir = tmp_path / ".project" / "sessions" / "wip" / "test-related"

        # Create related directories (tasks, qa)
        tasks_dir = session_dir / "tasks"
        qa_dir = session_dir / "qa"
        tasks_dir.mkdir()
        qa_dir.mkdir()

        # Create dummy files
        (tasks_dir / "task-1.md").write_text("# Task 1")
        (qa_dir / "qa-1.md").write_text("# QA 1")

        # Transition session
        session.state = "done"
        repo.save(session)

        # Verify everything moved together
        new_session_dir = tmp_path / ".project" / "sessions" / "done" / "test-related"
        assert (new_session_dir / "session.json").exists()
        assert (new_session_dir / "tasks" / "task-1.md").exists()
        assert (new_session_dir / "qa" / "qa-1.md").exists()

        # Verify old location is completely gone
        assert not session_dir.exists()


@pytest.mark.session
class TestNestedLayoutBackwardCompatibility:
    """Test that existing nested layout files are read correctly."""

    def test_read_existing_nested_session(self, tmp_path: Path):
        """Should read existing nested layout sessions."""
        # Manually create a nested layout session
        session_dir = tmp_path / ".project" / "sessions" / "wip" / "existing-session"
        session_dir.mkdir(parents=True)

        session_data = {
            "id": "existing-session",
            "state": "active",
            "meta": {
                "owner": "existing-owner",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }

        session_file = session_dir / "session.json"
        session_file.write_text(json.dumps(session_data, indent=2))

        # Read with repository
        repo = SessionRepository(project_root=tmp_path)
        session = repo.get("existing-session")

        # Verify loaded correctly
        assert session is not None
        assert session.id == "existing-session"
        assert session.state == "active"
        assert session.owner == "existing-owner"
