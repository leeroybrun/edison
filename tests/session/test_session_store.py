import os
import pytest
from pathlib import Path
from edison.core.session import store
from edison.core.session.config import SessionConfig

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root and configures environment variables
    to point to it. ensuring PathResolver and ConfigManager use this root.
    """
    # Setup .edison/core/config structure in tmp_path
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    
    # Create defaults.yaml and session.yaml in tmp_path
    # We need to copy the real ones or write minimal ones for testing.
    # Writing minimal ones ensures we test the config loading logic too.
    
    import yaml
    
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "file_locking": {
            "timeout_seconds": 10.0,
            "poll_interval_seconds": 0.1,
            "fail_open": False,
        },
        "session": {
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64,
            }
        },
    }
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
                "active": "active",
                "done": "done",
                "closing": "closing",
                "validated": "validated"
            },
            "defaults": {
                "initialState": "draft"
            },
            "lookupOrder": ["draft", "active", "done", "validated", "closing"]
        }
    }
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))
    
    # Create template file
    template_dir = tmp_path / ".agents" / "sessions"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "TEMPLATE.json").write_text("{}")

    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path)) # Just in case
    
    # Clear any cached config or paths
    # This is tricky if singletons are used. 
    # SessionConfig creates a new ConfigManager each time, so it should be fine
    # IF we re-instantiate SessionConfig or if store._CONFIG is re-initialized.
    # store._CONFIG is a module-level global. We might need to reload the module
    # or patch the global.
    
    # Re-initialize store._CONFIG
    store._CONFIG = SessionConfig()
    
    return tmp_path

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
    """Ensure maxLength must be configured in YAML (no hardcoded fallback)."""
    import yaml

    config_dir = project_root / ".edison" / "core" / "config"

    # Remove maxLength from session.yaml to simulate missing configuration override
    session_path = config_dir / "session.yaml"
    session_cfg = yaml.safe_load(session_path.read_text()) or {}
    session_cfg.setdefault("session", {}).setdefault("validation", {}).pop("maxLength", None)
    session_path.write_text(yaml.dump(session_cfg))

    # Ensure defaults.yaml does not provide maxLength either
    defaults_path = config_dir / "defaults.yaml"
    defaults_cfg = yaml.safe_load(defaults_path.read_text()) or {}
    defaults_cfg.pop("session", None)
    defaults_path.write_text(yaml.dump(defaults_cfg))

    store.reset_session_store_cache()

    with pytest.raises(ValueError, match="maxLength"):
        store.sanitize_session_id("any")

def test_session_dirs_creation(project_root):
    """Test that _ensure_session_dirs creates configured directories."""
    store._ensure_session_dirs()
    
    sessions_root = project_root / ".project" / "sessions"
    assert sessions_root.exists()
    assert (sessions_root / "draft").exists()
    assert (sessions_root / "active").exists()
    assert (sessions_root / "done").exists()
    assert (sessions_root / "closing").exists()
    assert (sessions_root / "validated").exists()

def test_save_and_load_session(project_root):
    """Test saving and loading a session."""
    sid = "test-session"
    data = {"id": sid, "foo": "bar"}
    
    store.save_session(sid, data)
    
    assert store.session_exists(sid)
    
    loaded = store.load_session(sid)
    assert loaded["id"] == sid
    assert loaded["foo"] == "bar"
    
    # Verify file location (white-box test of implementation detail, but useful)
    # Verify file created in correct location (Draft by default)
    expected_path = project_root / ".project" / "sessions" / "draft" / "test-session" / "session.json"
    assert expected_path.exists()

def test_load_session_not_found(project_root):
    with pytest.raises(store.SessionNotFoundError):
        store.load_session("non-existent")

def test_read_template(project_root):
    """Test reading the session template."""
    # We created a empty template in fixture
    template = store._read_template()
    assert template == {}
