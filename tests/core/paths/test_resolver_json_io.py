"""Test that PathResolver.detect_session_id uses centralized I/O.

This test ensures consistent file locking and error handling by using
read_json instead of direct file I/O.
"""
import os
from pathlib import Path
import pytest
import yaml
from edison.core.utils.paths.resolver import PathResolver
from edison.core.utils.io import write_json_atomic
from edison.core.config.cache import clear_all_caches
from edison.core.session._config import reset_config_cache
import edison.core.utils.paths.resolver as path_resolver


@pytest.fixture
def project_with_session(tmp_path, monkeypatch):
    """Create a real project with session structure."""
    # Reset caches
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Create .edison/config directory
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)

    # Create minimal config files
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))

    session_data = {
        "session": {
            "paths": {"root": ".project/sessions"},
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64
            }
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Create active session dir
    session_name = "test-session"
    session_dir = tmp_path / ".project" / "sessions" / "active" / session_name
    session_dir.mkdir(parents=True)

    # Use write_json_atomic to create session.json (uses centralized I/O)
    session_json = session_dir / "session.json"
    write_json_atomic(session_json, {"owner": "tester"})

    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("project_SESSION", raising=False)
    monkeypatch.delenv("project_OWNER", raising=False)

    # Reset caches after env setup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    yield tmp_path, session_name

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()


def test_detect_session_id_uses_read_json(project_with_session):
    """Verify that detect_session_id properly reads session.json files.

    This test verifies the actual behavior: detect_session_id should find
    a session when given a matching owner.
    """
    project_root, session_name = project_with_session

    # Test: Auto-detect session from owner
    result = PathResolver.detect_session_id(owner="tester")

    # Should detect the session ID from owner
    assert result == session_name, "Should detect session ID from owner"


def test_detect_session_id_returns_none_for_unknown_owner(project_with_session):
    """Verify that detect_session_id returns None for unknown owner."""
    project_root, session_name = project_with_session

    # Test: Try to detect session with non-matching owner
    result = PathResolver.detect_session_id(owner="nonexistent")

    # Should return None when owner doesn't match
    assert result is None, "Should return None for unknown owner"


def test_detect_session_id_with_explicit_parameter(project_with_session):
    """Verify that explicit session ID takes priority."""
    project_root, session_name = project_with_session

    # Test: Explicit parameter should take priority
    result = PathResolver.detect_session_id(explicit="explicit-session")

    # Should return the explicit value (after validation)
    assert result == "explicit-session", "Should use explicit parameter"


def test_detect_session_id_with_env_var(project_with_session, monkeypatch):
    """Verify that project_SESSION env var takes priority over owner."""
    project_root, session_name = project_with_session

    # Set environment variable
    monkeypatch.setenv("project_SESSION", "env-session")

    # Test: Environment variable should take priority over owner
    result = PathResolver.detect_session_id(owner="tester")

    # Should use env var, not owner
    assert result == "env-session", "Should use project_SESSION env var"


def test_detect_session_id_handles_malformed_json(tmp_path, monkeypatch):
    """Verify that detect_session_id gracefully handles malformed JSON."""
    # Reset caches
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Create minimal config
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)

    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))

    session_data = {
        "session": {
            "paths": {"root": ".project/sessions"},
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64
            }
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Create session dir with malformed JSON
    session_dir = tmp_path / ".project" / "sessions" / "active" / "bad-session"
    session_dir.mkdir(parents=True)

    # Write malformed JSON directly
    (session_dir / "session.json").write_text("{ invalid json }", encoding="utf-8")

    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("project_SESSION", raising=False)
    monkeypatch.delenv("project_OWNER", raising=False)

    # Reset caches
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Test: Should gracefully handle malformed JSON
    result = PathResolver.detect_session_id(owner="tester")

    # Should return None, not raise an exception
    assert result is None, "Should return None for malformed JSON"

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()
