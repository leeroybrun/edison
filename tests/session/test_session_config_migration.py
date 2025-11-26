import pytest
from pathlib import Path
import json
from edison.core.config.domains import SessionConfig
from edison.core.utils.paths.project import get_project_config_dir
from edison.core.utils.paths.resolver import PathResolver

def test_get_worktree_config_reads_manifest(tmp_path, monkeypatch):
    """Test that worktree config is read from manifest.json using read_json_safe logic."""
    
    # Mock project root
    root = tmp_path / "project"
    root.mkdir()
    
    # Mock .edison/config/manifest.json
    config_dir = get_project_config_dir(root)
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config_dir / "manifest.json"
    
    manifest_data = {
        "worktrees": {
            "enabled": True,
            "baseBranch": "develop"
        }
    }
    manifest_path.write_text(json.dumps(manifest_data))
    
    # Mock PathResolver to return our temp root
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: root)
    
    # Initialize config
    config = SessionConfig(repo_root=root)
    
    # Act
    wt_config = config.get_worktree_config()
    
    # Assert
    assert wt_config["enabled"] is True
    assert wt_config["baseBranch"] == "develop"

def test_get_worktree_config_handles_malformed_json(tmp_path, monkeypatch):
    """Test resilience against bad JSON in manifest."""
    root = tmp_path / "project"
    root.mkdir()
    config_dir = get_project_config_dir(root)
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config_dir / "manifest.json"
    
    # Write invalid JSON
    manifest_path.write_text("{invalid json")
    
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: root)
    
    config = SessionConfig(repo_root=root)
    
    # Should not raise, should return defaults
    wt_config = config.get_worktree_config()
    assert wt_config["enabled"] is True # default
    assert wt_config["baseBranch"] == "main" # default
