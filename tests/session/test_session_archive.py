import os
import pytest
import tarfile
from pathlib import Path
import yaml
from edison.core.session import archive
from edison.core.session.repository import SessionRepository
from edison.core.session.id import validate_session_id
from edison.core.session._config import reset_config_cache, get_config
from edison.core.config.domains import SessionConfig
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

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root.
    """
    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "session": {
            "paths": {
                "root": ".project/sessions",
                "archive": ".project/archive"
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
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))

    # Reload configs
    reset_config_cache()
    archive._CONFIG = SessionConfig()

    return tmp_path

def test_archive_session(project_root):
    """Test archiving a session."""
    sid = "test-archive"
    
    # Create a dummy session
    _ensure_session_dirs()
    sess_dir = _session_dir("active", sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "session.json").write_text("{}")
    (sess_dir / "data.txt").write_text("some data")
    
    # Archive it
    archive_path = archive.archive_session(sid)
    
    assert archive_path.exists()
    assert archive_path.name == f"{sid}.tar.gz"
    
    # Verify archive content
    with tarfile.open(archive_path, "r:gz") as tf:
        names = tf.getnames()
        assert "session.json" in names
        assert "data.txt" in names

def test_archive_path_structure(project_root):
    """Test archive path structure (YYYY-MM)."""
    sid = "test-structure"
    path = archive._archive_path_for_session(sid)
    
    # Check it contains YYYY-MM
    import datetime
    stamp = datetime.datetime.now().strftime("%Y-%m")
    assert stamp in str(path)
    assert path.name == f"{sid}.tar.gz"
