import os
from pathlib import Path
import pytest
import yaml
from edison.core.utils.paths.management import get_management_paths
from edison.core.utils.paths.project import get_project_config_dir

def test_management_config_loaded_from_resolved_dir(tmp_path, monkeypatch):
    """Verify that management config is loaded from the resolved project config dir."""
    monkeypatch.chdir(tmp_path)
    
    # Setup .edison/config.yml (resolved default)
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    (edison_dir / "config.yml").write_text("paths:\n  management_dir: .custom_mgmt_edison")
    
    # Setup .agents/config.yml (legacy - should be ignored if logic is fixed)
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.yml").write_text("paths:\n  management_dir: .legacy_mgmt_agents")
    
    # Force resolution to default (.edison)
    monkeypatch.delenv("EDISON_paths__project_config_dir", raising=False)
    
    # Get paths
    paths = get_management_paths(repo_root=tmp_path)
    # Force reload of config for the test instance
    paths._config = paths._load_config()
    
    # Should pick up .edison config, NOT .agents
    # Currently this fails (RED) because it hardcodes .agents
    assert paths.get_management_root().name == ".custom_mgmt_edison"

def test_management_config_respects_env_var_override(tmp_path, monkeypatch):
    """Verify that management config follows the environment variable override for config dir."""
    monkeypatch.chdir(tmp_path)
    
    # Setup custom config dir
    custom_config = tmp_path / ".custom_conf"
    custom_config.mkdir()
    (custom_config / "config.yml").write_text("paths:\n  management_dir: .env_mgmt")
    
    # Set env var
    monkeypatch.setenv("EDISON_paths__project_config_dir", ".custom_conf")
    
    # Get paths
    paths = get_management_paths(repo_root=tmp_path)
    paths._config = paths._load_config()
    
    assert paths.get_management_root().name == ".env_mgmt"
