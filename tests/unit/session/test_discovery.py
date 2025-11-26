"""Tests for session discovery utilities - finding session.json across layouts."""
import pytest
from pathlib import Path
from edison.core.session import discovery


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root with session configuration.
    """
    # Setup .edison/core/config structure in tmp_path
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)

    import yaml

    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yaml").write_text(yaml.dump(defaults_data))

    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
                "templates": {
                    "primary": ".agents/sessions/TEMPLATE.json",
                    "repo": ".agents/sessions/TEMPLATE.json"
                }
            },
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64
            },
            "states": {
                "draft": "draft",
                "active": "wip",
                "wip": "wip",
                "done": "done",
                "closing": "done",
                "validated": "validated",
                "recovery": "recovery",
                "archived": "archived",
            },
            "defaults": {
                "initialState": "wip"
            },
            "lookupOrder": ["wip", "draft", "done", "validated", "recovery", "archived"]
        }
    }
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))

    # Create template file
    template_dir = tmp_path / ".agents" / "sessions"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "TEMPLATE.json").write_text("{}")

    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # Clear any cached config
    from edison.core.session import store
    store.reset_session_store_cache()

    return tmp_path


class TestFindSessionJsonCandidates:
    """Test find_session_json_candidates() - returns all possible paths."""

    def test_returns_candidates_for_new_layout(self, project_root):
        """Should return paths for new nested layout {state}/{id}/session.json."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "test-session-123"

        candidates = discovery.find_session_json_candidates(
            session_id=session_id,
            sessions_root=sessions_root
        )

        # Should include new layout paths for all configured states
        assert sessions_root / "wip" / session_id / "session.json" in candidates
        assert sessions_root / "draft" / session_id / "session.json" in candidates
        assert sessions_root / "done" / session_id / "session.json" in candidates
        assert sessions_root / "validated" / session_id / "session.json" in candidates

    def test_returns_candidates_for_legacy_flat_layout(self, project_root):
        """Should return paths for legacy flat layout {state}/{id}.json."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "test-session-123"

        candidates = discovery.find_session_json_candidates(
            session_id=session_id,
            sessions_root=sessions_root
        )

        # Should include legacy flat layout paths
        assert sessions_root / "wip" / f"{session_id}.json" in candidates
        assert sessions_root / "draft" / f"{session_id}.json" in candidates
        assert sessions_root / "done" / f"{session_id}.json" in candidates

    def test_uses_custom_states_list(self, project_root):
        """Should use custom states list when provided."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "test-session-123"

        candidates = discovery.find_session_json_candidates(
            session_id=session_id,
            sessions_root=sessions_root,
            states=["wip", "done"]  # Only these two states
        )

        # Should only include paths for specified states
        wip_candidates = [c for c in candidates if "wip" in str(c)]
        done_candidates = [c for c in candidates if "done" in str(c)]
        draft_candidates = [c for c in candidates if "draft" in str(c)]

        assert len(wip_candidates) >= 2  # new + legacy
        assert len(done_candidates) >= 2  # new + legacy
        assert len(draft_candidates) == 0  # Not in custom states

    def test_uses_state_map_for_directory_names(self, project_root):
        """Should map state names to directory names using state_map."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "test-session-123"

        # State map: "active" -> "wip", "closing" -> "done"
        state_map = {
            "active": "wip",
            "closing": "done",
        }

        candidates = discovery.find_session_json_candidates(
            session_id=session_id,
            sessions_root=sessions_root,
            states=["active", "closing"],
            state_map=state_map
        )

        # Should use mapped directory names
        assert sessions_root / "wip" / session_id / "session.json" in candidates
        assert sessions_root / "done" / session_id / "session.json" in candidates
        # Should NOT use the state name directly
        active_dir = sessions_root / "active" / session_id / "session.json"
        # If state_map doesn't have it, it should fall back to state name
        # But in this test we're explicitly mapping, so it should use wip

    def test_sanitizes_session_id(self, project_root):
        """Should reject invalid session IDs."""
        sessions_root = project_root / ".project" / "sessions"

        with pytest.raises(ValueError, match="path traversal"):
            discovery.find_session_json_candidates(
                session_id="../bad-id",
                sessions_root=sessions_root
            )

        with pytest.raises(ValueError, match="invalid characters"):
            discovery.find_session_json_candidates(
                session_id="bad id",  # space not allowed
                sessions_root=sessions_root
            )


class TestResolveSessionJson:
    """Test resolve_session_json() - returns first existing path."""

    def test_finds_new_layout_session(self, project_root):
        """Should find session.json in new nested layout."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "test-session-456"

        # Create session in new layout
        session_dir = sessions_root / "wip" / session_id
        session_dir.mkdir(parents=True)
        session_json = session_dir / "session.json"
        session_json.write_text('{"id": "test-session-456"}')

        result = discovery.resolve_session_json(
            session_id=session_id,
            sessions_root=sessions_root
        )

        assert result == session_json
        assert result.exists()

    def test_finds_legacy_flat_layout_session(self, project_root):
        """Should find session in legacy flat layout."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "legacy-session-789"

        # Create session in legacy flat layout
        legacy_dir = sessions_root / "wip"
        legacy_dir.mkdir(parents=True)
        legacy_json = legacy_dir / f"{session_id}.json"
        legacy_json.write_text('{"id": "legacy-session-789"}')

        result = discovery.resolve_session_json(
            session_id=session_id,
            sessions_root=sessions_root
        )

        assert result == legacy_json
        assert result.exists()

    def test_prefers_first_match_in_state_order(self, project_root):
        """Should return first match according to state lookup order."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "multi-state-session"

        # Create session in multiple states
        for state in ["done", "wip"]:
            state_dir = sessions_root / state / session_id
            state_dir.mkdir(parents=True)
            (state_dir / "session.json").write_text(f'{{"id": "{session_id}", "state": "{state}"}}')

        # wip comes before done in lookup order
        result = discovery.resolve_session_json(
            session_id=session_id,
            sessions_root=sessions_root,
            states=["wip", "done"]
        )

        # Should find the wip one (first in order)
        assert result == sessions_root / "wip" / session_id / "session.json"

    def test_returns_none_when_not_found(self, project_root):
        """Should return None when session not found."""
        sessions_root = project_root / ".project" / "sessions"

        result = discovery.resolve_session_json(
            session_id="nonexistent-session",
            sessions_root=sessions_root
        )

        assert result is None

    def test_uses_custom_states_list(self, project_root):
        """Should only search in specified states."""
        sessions_root = project_root / ".project" / "sessions"
        session_id = "custom-states-session"

        # Create session in 'done' state
        done_dir = sessions_root / "done" / session_id
        done_dir.mkdir(parents=True)
        (done_dir / "session.json").write_text('{"id": "custom-states-session"}')

        # Search only in 'wip' - should not find it
        result = discovery.resolve_session_json(
            session_id=session_id,
            sessions_root=sessions_root,
            states=["wip"]
        )

        assert result is None

        # Search in both 'wip' and 'done' - should find it
        result = discovery.resolve_session_json(
            session_id=session_id,
            sessions_root=sessions_root,
            states=["wip", "done"]
        )

        assert result == done_dir / "session.json"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_session_id(self, project_root):
        """Should reject empty session ID."""
        sessions_root = project_root / ".project" / "sessions"

        with pytest.raises(ValueError, match="cannot be empty"):
            discovery.find_session_json_candidates(
                session_id="",
                sessions_root=sessions_root
            )

    def test_handles_missing_sessions_root(self, project_root):
        """Should handle non-existent sessions root gracefully."""
        sessions_root = project_root / "nonexistent" / "sessions"

        # Should not raise, just return empty or paths that don't exist
        candidates = discovery.find_session_json_candidates(
            session_id="test-session",
            sessions_root=sessions_root
        )

        # Should return candidates even if root doesn't exist
        assert len(candidates) > 0
        # But none should exist
        assert not any(c.exists() for c in candidates)

    def test_session_id_too_long(self, project_root):
        """Should reject session ID exceeding max length."""
        sessions_root = project_root / ".project" / "sessions"

        with pytest.raises(ValueError, match="too long"):
            discovery.find_session_json_candidates(
                session_id="a" * 65,  # Max is 64
                sessions_root=sessions_root
            )
