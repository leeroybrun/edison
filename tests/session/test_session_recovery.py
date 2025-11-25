import os
import pytest
import yaml
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from edison.core.session import recovery
from edison.core.session import store
from edison.core.session.config import SessionConfig

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root.
    """
    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yaml").write_text(yaml.dump(defaults_data))
    
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
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    
    # Reload configs
    store._CONFIG = SessionConfig()
    recovery._CONFIG = SessionConfig()
    
    return tmp_path

def test_is_session_expired(project_root):
    """Test session expiration logic."""
    sid = "sess-expired"
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
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
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
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
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text('{"state": "active"}')
    
    rec_dir = recovery.handle_timeout(sess_dir)
    
    assert not sess_dir.exists()
    assert rec_dir.exists()
    assert rec_dir.parent.name == "recovery"
    assert (rec_dir / "recovery.json").exists()
    
    data = json.loads((rec_dir / "session.json").read_text())
    assert data["state"] == "Recovery"
