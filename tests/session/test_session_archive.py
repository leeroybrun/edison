import os
import pytest
import tarfile
from pathlib import Path
import yaml
from edison.core.session import archive
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
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    
    # Reload configs
    store._CONFIG = SessionConfig()
    archive._CONFIG = SessionConfig()
    
    return tmp_path

def test_archive_session(project_root):
    """Test archiving a session."""
    sid = "test-archive"
    
    # Create a dummy session
    store._ensure_session_dirs()
    sess_dir = store._session_dir("active", sid)
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
