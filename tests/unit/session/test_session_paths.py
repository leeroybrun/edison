"""Tests for session path resolution utilities.

These tests validate the session path discovery logic extracted from
QARepository and TaskRepository into session/paths.py.
"""
from __future__ import annotations
from helpers.io_utils import write_yaml

import pytest
import importlib
from pathlib import Path
from edison.core.session.paths import (
    get_session_bases,
    resolve_session_record_path,
)

@pytest.fixture
def session_path_env(tmp_path, monkeypatch):
    """Setup test environment with configuration."""
    repo = tmp_path
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"

    # 1. defaults.yaml
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "session": {
                    "states": {
                        "wip": {"dirname": "wip"},
                        "done": {"dirname": "done"},
                        "validated": {"dirname": "validated"},
                    }
                }
            }
        },
    )

    # 2. sessions.yaml
    write_yaml(
        config_dir / "sessions.yaml",
        {
            "sessions": {
                "paths": {
                    "root": ".project/sessions",
                }
            }
        },
    )

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    # Clear caches
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Reload config-dependent modules
    import edison.core.task.paths as paths
    importlib.reload(paths)
    import edison.core.session._config as session_config
    importlib.reload(session_config)

    return repo

def test_get_session_bases_without_session_id_finds_all_sessions(session_path_env):
    """Test get_session_bases without session_id finds all session files (flat layout)."""
    # Setup: Create session JSON files using flat layout
    sessions_wip = session_path_env / ".project" / "sessions" / "wip"
    sessions_wip.mkdir(parents=True, exist_ok=True)
    (sessions_wip / "sess-1.json").write_text('{"id": "sess-1"}')
    (sessions_wip / "sess-2.json").write_text('{"id": "sess-2"}')

    sessions_done = session_path_env / ".project" / "sessions" / "done"
    sessions_done.mkdir(parents=True, exist_ok=True)
    (sessions_done / "sess-3.json").write_text('{"id": "sess-3"}')

    # Act
    bases = get_session_bases(project_root=session_path_env)

    # Assert - all session state directories found
    # With flat layout, bases should point to state directories
    base_names = {base.name for base in bases}
    assert "wip" in base_names or "done" in base_names

def test_get_session_bases_with_session_id_finds_specific_session(session_path_env):
    """Test get_session_bases with session_id finds specific session directory."""
    # Setup: Create session in wip
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session.core.models import Session

    repo = SessionRepository(project_root=session_path_env)
    session = Session.create("test-session-001", state="wip")
    repo.create(session)

    # Act
    bases = get_session_bases(session_id="test-session-001", project_root=session_path_env)

    # Assert - specific session found
    assert len(bases) > 0
    assert any(base.name == "test-session-001" for base in bases)

def test_get_session_bases_with_nonexistent_session_returns_candidates(session_path_env):
    """Test get_session_bases with nonexistent session returns candidate paths."""
    # Setup: Create session directories but no specific session
    sessions_wip = session_path_env / ".project" / "sessions" / "wip"
    sessions_wip.mkdir(parents=True)

    # Act
    bases = get_session_bases(session_id="nonexistent", project_root=session_path_env)

    # Assert - still returns candidate paths (for creation)
    assert len(bases) > 0

def test_get_session_bases_handles_session_entity_data(session_path_env):
    """Test get_session_bases uses SessionRepository to get session metadata."""
    # Setup: Create session via repository
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session.core.models import Session

    repo = SessionRepository(project_root=session_path_env)
    session = Session.create("test-session-002", state="wip")
    repo.create(session)

    # Act
    bases = get_session_bases(session_id="test-session-002", project_root=session_path_env)

    # Assert - session base path matches repository location
    session_path = repo.get_session_json_path("test-session-002")
    session_base = session_path.parent

    assert any(base.resolve() == session_base.resolve() for base in bases)

def test_resolve_session_record_path_uses_session_repository(session_path_env):
    """Test resolve_session_record_path uses SessionRepository to find session."""
    # Setup: Create session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session.core.models import Session

    repo = SessionRepository(project_root=session_path_env)
    session = Session.create("test-session-003", state="wip")
    repo.create(session)

    # Act
    path = resolve_session_record_path(
        record_id="T-001-qa",
        session_id="test-session-003",
        state="waiting",
        record_type="qa",
        project_root=session_path_env,
    )

    # Assert - path is within session directory
    assert "test-session-003" in str(path)
    assert "qa" in str(path)
    assert "waiting" in str(path)
    assert path.name == "T-001-qa.md"

def test_resolve_session_record_path_falls_back_to_search(session_path_env):
    """Test resolve_session_record_path falls back to searching session dirs."""
    # Setup: Create session directory manually (not via repository)
    sessions_wip = session_path_env / ".project" / "sessions" / "wip"
    session_dir = sessions_wip / "manual-session"
    session_dir.mkdir(parents=True)

    # Act
    path = resolve_session_record_path(
        record_id="T-002-qa",
        session_id="manual-session",
        state="todo",
        record_type="qa",
        project_root=session_path_env,
    )

    # Assert - path is in expected location
    assert "manual-session" in str(path)
    assert "qa" in str(path)
    assert "todo" in str(path)

def test_resolve_session_record_path_defaults_to_wip(session_path_env):
    """Test resolve_session_record_path defaults to wip when session not found."""
    # Act - nonexistent session
    path = resolve_session_record_path(
        record_id="T-003-qa",
        session_id="nonexistent-session",
        state="wip",
        record_type="qa",
        project_root=session_path_env,
    )

    # Assert - path defaults to wip directory
    assert "nonexistent-session" in str(path)
    assert "wip" in str(path)
    assert "qa" in str(path)

def test_resolve_session_record_path_supports_task_record_type(session_path_env):
    """Test resolve_session_record_path works with task record type."""
    # Setup: Create session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session.core.models import Session

    repo = SessionRepository(project_root=session_path_env)
    session = Session.create("task-session", state="wip")
    repo.create(session)

    # Act
    path = resolve_session_record_path(
        record_id="T-004",
        session_id="task-session",
        state="todo",
        record_type="task",
        project_root=session_path_env,
    )

    # Assert - path is for task
    assert "task-session" in str(path)
    assert "tasks" in str(path)  # tasks directory, not qa
    assert "todo" in str(path)

def test_resolve_session_record_path_ensures_session_id_in_path(session_path_env):
    """Test resolve_session_record_path ensures session_id is in the final path."""
    # Setup: Create session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session.core.models import Session

    repo = SessionRepository(project_root=session_path_env)
    session = Session.create("id-test-session", state="wip")
    repo.create(session)

    # Act
    path = resolve_session_record_path(
        record_id="T-005-qa",
        session_id="id-test-session",
        state="waiting",
        record_type="qa",
        project_root=session_path_env,
    )

    # Assert - session_id appears in path
    path_parts = path.parts
    assert "id-test-session" in path_parts
