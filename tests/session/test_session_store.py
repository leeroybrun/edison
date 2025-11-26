import os
import pytest
from pathlib import Path
from edison.core.session import store
from edison.core.session.config import SessionConfig

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root and configures environment variables
    to point to it, ensuring PathResolver and ConfigManager use this root.

    Setup order is critical:
    1. Create directory structure FIRST
    2. Write config files SECOND
    3. Set environment variables THIRD
    4. Reset caches LAST (after everything is set up)
    """
    import yaml

    # STEP 1: Create directory structure
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)

    template_dir = tmp_path / ".agents" / "sessions"
    template_dir.mkdir(parents=True, exist_ok=True)

    # STEP 2: Write config files
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
    (template_dir / "TEMPLATE.json").write_text("{}")

    # STEP 3: Set environment variables
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # STEP 4: Reset all caches LAST (after env vars are set and files exist)
    # This ensures PathResolver and SessionConfig pick up the test configuration
    store.reset_session_store_cache()

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
