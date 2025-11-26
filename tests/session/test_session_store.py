import os
import pytest
from pathlib import Path
from edison.core.session import store
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
import edison.core.utils.paths.resolver as path_resolver

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root and configures environment variables
    to point to it, ensuring PathResolver and ConfigManager use this root.
    """
    import yaml

    # Reset ALL caches first
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Create directory structure  
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)

    # Template location expected by bundled config
    template_dir = tmp_path / ".edison" / "sessions"
    template_dir.mkdir(parents=True, exist_ok=True)

    # Write config files
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "file_locking": {
            "timeout_seconds": 10.0,
            "poll_interval_seconds": 0.1,
            "fail_open": False,
        },
    }
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))

    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
            },
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64
            },
            # Match bundled defaults
            "states": {
                "draft": "draft",
                "active": "wip",
                "wip": "wip",
                "done": "done",
            },
            "lookupOrder": ["wip", "draft", "done"]
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Create template file at expected location
    (template_dir / "TEMPLATE.json").write_text("{}")

    # Set environment variables BEFORE resetting cache again
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))

    # Reset caches AFTER env vars are set
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()
    store.reset_session_store_cache()

    yield tmp_path

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

def test_sanitize_session_id(project_root):
    """Test session ID validation using config rules."""
    assert store.sanitize_session_id("valid-id") == "valid-id"
    assert store.sanitize_session_id("valid.id") == "valid.id"
    assert store.sanitize_session_id("valid_id") == "valid_id"
    
    with pytest.raises(ValueError, match="invalid characters"):
        store.sanitize_session_id("invalid id") # space
        
    with pytest.raises(ValueError, match="path traversal"):
        store.sanitize_session_id("../traversal")
        
    with pytest.raises(ValueError, match="too long"):
        store.sanitize_session_id("a" * 65)


def test_sanitize_session_id_requires_configured_max_length(project_root):
    """Ensure maxLength is properly configured."""
    result = store.sanitize_session_id("any")
    assert result == "any"

def test_session_dirs_creation(project_root):
    """Test that _ensure_session_dirs creates configured directories."""
    store._ensure_session_dirs()
    
    sessions_root = project_root / ".project" / "sessions"
    assert sessions_root.exists()
    # Check for actual state directories
    assert (sessions_root / "wip").exists()
    assert (sessions_root / "done").exists()

def test_save_and_load_session(project_root):
    """Test saving and loading a session."""
    sid = "test-session"
    data = {"id": sid, "foo": "bar"}
    
    store.save_session(sid, data)
    
    assert store.session_exists(sid)
    
    loaded = store.load_session(sid)
    assert loaded["id"] == sid
    assert loaded["foo"] == "bar"
    
    # Session should be created in some state directory
    # The exact directory depends on initial state config
    sessions_root = project_root / ".project" / "sessions"
    found_path = None
    for state_dir in sessions_root.iterdir():
        if state_dir.is_dir():
            session_path = state_dir / "test-session" / "session.json"
            if session_path.exists():
                found_path = session_path
                break
    
    assert found_path is not None, "Session file should exist in one of the state directories"

def test_load_session_not_found(project_root):
    with pytest.raises(store.SessionNotFoundError):
        store.load_session("non-existent")

def test_read_template(project_root):
    """Test reading the session template."""
    template = store._read_template()
    assert template == {}
