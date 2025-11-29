import pytest
import yaml
from pathlib import Path
from edison.core.session import database
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches

@pytest.fixture(autouse=True)
def setup_custom_config(project_root):
    """Setup custom database configuration and adapter."""
    config_dir = project_root / ".edison" / "config"
    
    defaults_data = {
        "edison": {"version": "1.0.0"},
        "database": {
            "enabled": True,
            "adapter": "test-adapter",
            "sessionPrefix": "test_session",
            "url": "sqldb://user:pass@localhost:5432/base",
            "cleanupStrategy": "drop"
        }
    }
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))
    
    # Create dummy adapter in packs directory
    packs_dir = project_root / ".edison" / "packs" / "test-adapter"
    packs_dir.mkdir(parents=True, exist_ok=True)
    
    adapter_code = '''
def create_session_database(session_id, db_prefix, base_db_url, repo_dir, worktree_config):
    return f"{base_db_url}/{db_prefix}_{session_id}"

def drop_session_database(session_id, db_prefix, base_db_url, repo_dir, worktree_config):
    # Write to a file to verify call
    (repo_dir / "dropped.txt").write_text(f"Dropped {session_id}")
'''
    (packs_dir / "db_adapter.py").write_text(adapter_code)
    
    # Reset caches
    clear_all_caches()
    reset_config_cache()

def test_get_database_url(project_root):
    """Test getting database URL from config."""
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
    config_path = project_root / ".edison" / "config" / "defaults.yml"
    data = yaml.safe_load(config_path.read_text())
    data["database"]["enabled"] = False
    config_path.write_text(yaml.dump(data))
    
    # Reset config cache
    clear_all_caches()
    reset_config_cache()
    
    assert database.create_session_database("sess123") is None
