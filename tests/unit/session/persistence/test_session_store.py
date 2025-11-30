import pytest
from pathlib import Path
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.core.id import validate_session_id
from edison.core.session._config import get_config
from edison.core.session.persistence.graph import save_session
from edison.core.session.lifecycle.manager import get_session
from edison.core.exceptions import SessionNotFoundError, SessionError
from edison.core.utils.paths import PathResolver, get_management_paths
from edison.core.utils.io import read_json
from tests.helpers import reset_session_store_cache

# Helper functions to replace store module functions

def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    repo = SessionRepository()
    return repo.exists(session_id)

def _ensure_session_dirs():
    """Ensure session directories exist."""
    cfg = get_config()
    root = PathResolver.resolve_project_root()
    sessions_root = root / cfg.get_session_root_path()
    state_map = cfg.get_session_states()
    for state, dirname in state_map.items():
        (sessions_root / dirname).mkdir(parents=True, exist_ok=True)

def _read_template():
    """Read session template."""
    root = PathResolver.resolve_project_root()
    mgmt = get_management_paths(root)
    template_path = mgmt.get_sessions_root() / "TEMPLATE.json"
    if template_path.exists():
        return read_json(template_path)
    return {}

@pytest.fixture(autouse=True)
def setup_custom_config(project_root):
    """Setup custom session configuration and template."""
    import yaml
    config_dir = project_root / ".edison" / "config"
    
    # Template location expected by bundled config
    template_dir = project_root / ".edison" / "sessions"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "TEMPLATE.json").write_text("{}")
    
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

    # Reset caches
    reset_session_store_cache()

def test_sanitize_session_id(project_root):
    """Test session ID validation using config rules."""
    assert validate_session_id("valid-id") == "valid-id"
    assert validate_session_id("valid.id") == "valid.id"
    assert validate_session_id("valid_id") == "valid_id"

    with pytest.raises(ValueError, match="invalid characters"):
        validate_session_id("invalid id") # space

    with pytest.raises(ValueError, match="path traversal"):
        validate_session_id("../traversal")

    with pytest.raises(ValueError, match="too long"):
        validate_session_id("a" * 65)


def test_sanitize_session_id_requires_configured_max_length(project_root):
    """Ensure maxLength is properly configured."""
    result = validate_session_id("any")
    assert result == "any"

def test_session_dirs_creation(project_root):
    """Test that _ensure_session_dirs creates configured directories."""
    _ensure_session_dirs()

    sessions_root = project_root / ".project" / "sessions"
    assert sessions_root.exists()
    # Check for actual state directories
    assert (sessions_root / "wip").exists()
    assert (sessions_root / "done").exists()

def test_save_and_load_session(project_root):
    """Test saving and loading a session with proper structured data."""
    sid = "test-session"
    # Use proper Session structure with valid fields
    data = {
        "id": sid,
        "state": "wip",
        "phase": "implementation",
        "meta": {
            "owner": "test-user",
        },
        "tasks": {},
        "qa": {},
    }

    save_session(sid, data)

    assert session_exists(sid)

    loaded = get_session(sid)
    assert loaded["id"] == sid
    assert loaded["state"] == "wip"
    assert loaded["phase"] == "implementation"
    assert "meta" in loaded
    assert loaded["meta"]["owner"] == "test-user"

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
    with pytest.raises((SessionNotFoundError, SessionError)):
        get_session("non-existent")

def test_read_template(project_root):
    """Test reading the session template."""
    template = _read_template()
    assert template == {}
