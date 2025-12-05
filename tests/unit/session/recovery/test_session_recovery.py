import pytest
import yaml
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from edison.core.session import recovery
from edison.core.session._config import get_config
from edison.core.utils.paths import PathResolver
from tests.helpers import reset_session_store_cache

def _ensure_session_dirs():
    """Ensure session directories exist."""
    cfg = get_config()
    root = PathResolver.resolve_project_root()
    sessions_root = root / cfg.get_session_root_path()
    state_map = cfg.get_session_states()
    for state, dirname in state_map.items():
        (sessions_root / dirname).mkdir(parents=True, exist_ok=True)

def _session_dir(state: str, session_id: str) -> Path:
    """Get session directory."""
    cfg = get_config()
    root = PathResolver.resolve_project_root()
    sessions_root = root / cfg.get_session_root_path()
    state_map = cfg.get_session_states()
    dirname = state_map.get(state, state)
    return sessions_root / dirname / session_id

@pytest.fixture(autouse=True)
def setup_custom_config(project_root):
    """Setup custom session configuration for recovery tests."""
    config_dir = project_root / ".edison" / "config"
    
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
                "tx": ".project/sessions/_tx"
            },
            "recovery": {
                "timeoutHours": 1,
                "clockSkewAllowanceSeconds": 60
            },
            "validation": {
                "idRegex": r"^[a-zA-Z0-9_\-\.]+$",
                "maxLength": 64
            },
            "states": {
                "active": "active",
                "closing": "closing",
                "validated": "validated"
            }
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))
    
    # Reset caches
    reset_session_store_cache()

def test_is_session_expired(project_root):
    """Test session expiration logic."""
    sid = "sess-expired"
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    
    # Case 1: No meta -> expired
    (sess_dir / "session.json").write_text("{}")
    assert recovery.is_session_expired(sid) is True
    
    # Case 2: Active recently -> not expired
    now = datetime.now(timezone.utc)
    meta = {
        "meta": {
            "lastActive": now.isoformat()
        }
    }
    (sess_dir / "session.json").write_text(json.dumps(meta))
    assert recovery.is_session_expired(sid) is False
    
    # Case 3: Expired (older than 1 hour)
    old = now - timedelta(hours=2)
    meta["meta"]["lastActive"] = old.isoformat()
    (sess_dir / "session.json").write_text(json.dumps(meta))
    assert recovery.is_session_expired(sid) is True

def test_check_timeout(project_root):
    """Test check_timeout function."""
    sid = "sess-timeout"
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now(timezone.utc)
    
    # Not timed out
    meta = {"last_active_at": now.isoformat()}
    (sess_dir / "session.json").write_text(json.dumps(meta))
    assert recovery.check_timeout(sess_dir, threshold_minutes=60) is False
    
    # Timed out
    old = now - timedelta(minutes=61)
    meta["last_active_at"] = old.isoformat()
    (sess_dir / "session.json").write_text(json.dumps(meta))
    assert recovery.check_timeout(sess_dir, threshold_minutes=60) is True

def test_handle_timeout(project_root):
    """Test handle_timeout moves session to recovery."""
    sid = "sess-handle-timeout"
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text('{"state": "active"}')
    
    rec_dir = recovery.handle_timeout(sess_dir)
    
    assert not sess_dir.exists()
    assert rec_dir.exists()
    assert rec_dir.parent.name == "recovery"
    assert (rec_dir / "recovery.json").exists()
    
    data = json.loads((rec_dir / "session.json").read_text())
    assert data["state"] == "recovery"
