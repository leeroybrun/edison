import pytest
import yaml
import json
from pathlib import Path
from edison.core.session import transaction
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session._config import reset_config_cache, get_config
from edison.core.config.domains import SessionConfig
from edison.core.exceptions import SessionError
from edison.core.utils.paths import PathResolver

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
    """Setup custom session configuration and transaction timeouts."""
    config_dir = project_root / ".edison" / "config"
    
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "file_locking": {
            "timeout_seconds": 1,
            "poll_interval_seconds": 0.1,
            "fail_open": False
        },
        "timeouts": {
            "git_operations_seconds": 10,
            "db_operations_seconds": 5,
            "json_io_lock_seconds": 5
        }
    }
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
                "tx": ".project/sessions/_tx"
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
    
    # Reload configs
    reset_config_cache()
    transaction._CONFIG = SessionConfig()

def test_transaction_lifecycle(project_root):
    """Test begin, finalize, abort lifecycle."""
    sid = "sess-tx"
    
    # Create session
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    # Begin
    tx_id = transaction.begin_tx(sid, domain="test")
    assert tx_id
    
    tx_path = project_root / ".project" / "sessions" / "_tx" / sid / f"{tx_id}.json"
    assert tx_path.exists()
    data = json.loads(tx_path.read_text())
    assert data["sessionId"] == sid
    assert data["domain"] == "test"
    assert data["finalizedAt"] is None
    
    # Finalize
    transaction.finalize_tx(sid, tx_id)
    data = json.loads(tx_path.read_text())
    assert data["finalizedAt"] is not None
    
    # Abort
    tx_id2 = transaction.begin_tx(sid, domain="test2")
    transaction.abort_tx(sid, tx_id2, reason="oops")
    data = json.loads((tx_path.parent / f"{tx_id2}.json").read_text())
    assert data["abortedAt"] is not None
    assert data["reason"] == "oops"

def test_session_transaction_context(project_root):
    """Test context manager."""
    sid = "sess-ctx"
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    with transaction.session_transaction(sid, domain="ctx") as tx_id:
        assert tx_id
        tx_path = project_root / ".project" / "sessions" / "_tx" / sid / f"{tx_id}.json"
        assert tx_path.exists()
        
    # Should be committed
    data = json.loads(tx_path.read_text())
    assert data["finalizedAt"] is not None

def test_session_transaction_rollback(project_root):
    """Test context manager rollback on error."""
    sid = "sess-rollback"
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    
    tx_id_captured = None
    try:
        with transaction.session_transaction(sid, domain="rollback") as tx_id:
            tx_id_captured = tx_id
            raise ValueError("Boom")
    except ValueError:
        pass
        
    assert tx_id_captured
    tx_path = project_root / ".project" / "sessions" / "_tx" / sid / f"{tx_id_captured}.json"
    data = json.loads(tx_path.read_text())
    assert data["abortedAt"] is not None
    assert data["reason"] == "rollback"

def test_validation_transaction(project_root):
    """Test ValidationTransaction class."""
    sid = "sess-val"
    _ensure_session_dirs()

    # Create session using repository to ensure proper structure
    repo = SessionRepository()
    from edison.core.session.core.models import Session
    sess = Session.create(sid, state="active")
    repo.create(sess)
    sess_path = repo.get_session_json_path(sid)
    sess_dir = sess_path.parent

    vt = transaction.ValidationTransaction(sid, wave="w1")
    assert vt.tx_id
    assert vt.staging_root.exists()

    # Stage a file
    (vt.staging_root / "test.txt").write_text("staged content")

    # Commit
    vt.commit()

    # Verify applied to project root
    final_path = project_root / "test.txt"
    assert final_path.exists()
    assert final_path.read_text() == "staged content"

    # Verify log
    log_path = sess_dir / "validation-transactions.log"
    assert log_path.exists()
    logs = log_path.read_text().splitlines()
    assert len(logs) >= 2 # started, committed
