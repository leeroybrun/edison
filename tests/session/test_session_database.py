import os
import pytest
import yaml
from pathlib import Path
from edison.core.session import database
from edison.core.session.config import SessionConfig

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root with a dummy database adapter.
    """
    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "database": {
            "enabled": True,
            "adapter": "test-adapter",
            "sessionPrefix": "test_session",
            "cleanupStrategy": "drop"
        }
    }
    (config_dir / "defaults.yaml").write_text(yaml.dump(defaults_data))
    
    # Create dummy adapter
    adapter_dir = tmp_path / ".edison" / "packs" / "test-adapter"
    adapter_dir.mkdir(parents=True)
    
    adapter_code = """
def create_session_database(session_id, db_prefix, base_db_url, repo_dir, worktree_config):
    return f"{base_db_url}/{db_prefix}_{session_id}"

def drop_session_database(session_id, db_prefix, base_db_url, repo_dir, worktree_config):
    # Write to a file to verify call
    (repo_dir / "dropped.txt").write_text(f"Dropped {session_id}")
"""
    (adapter_dir / "db_adapter.py").write_text(adapter_code)
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "sqldb://user:pass@localhost:5432/base")
    
    # Reload config
    database._CONFIG = SessionConfig()
    
    return tmp_path

def test_get_database_url(project_root):
    """Test getting database URL from env."""
    assert database._get_database_url() == "sqldb://user:pass@localhost:5432/base"

def test_get_session_db_prefix(project_root):
    """Test getting session DB prefix from config."""
    assert database._get_session_db_prefix() == "test_session"

def test_load_database_adapter_module(project_root):
    """Test loading the configured adapter."""
    mod = database._load_database_adapter_module()
    assert mod is not None
    assert hasattr(mod, "create_session_database")

def test_create_session_database(project_root):
    """Test creating a session database via adapter."""
    sid = "sess123"
    url = database.create_session_database(sid)
    assert url == "sqldb://user:pass@localhost:5432/base/test_session_sess123"

def test_drop_session_database(project_root):
    """Test dropping a session database via adapter."""
    sid = "sess123"
    database.drop_session_database(sid)
    
    # Verify side effect
    assert (project_root / "dropped.txt").read_text() == f"Dropped {sid}"

def test_database_disabled(project_root):
    """Test behavior when database is disabled."""
    # Update config to disable
    config_path = project_root / ".edison" / "core" / "config" / "defaults.yaml"
    data = yaml.safe_load(config_path.read_text())
    data["database"]["enabled"] = False
    config_path.write_text(yaml.dump(data))
    
    # Reload config
    database._CONFIG = SessionConfig()
    
    assert database.create_session_database("sess123") is None
