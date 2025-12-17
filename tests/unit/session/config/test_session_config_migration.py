import pytest
from pathlib import Path
import json
from edison.core.config.domains import SessionConfig
from edison.core.utils.paths.project import get_project_config_dir

def test_get_worktree_config_reads_manifest(isolated_project_env):
    """Test that worktree config is read from manifest.json using read_json_safe logic."""

    # Use isolated project environment (real directory structure)
    root = isolated_project_env

    # Create .edison/config/manifest.json
    config_dir = get_project_config_dir(root)
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config_dir / "manifest.json"

    manifest_data = {
        "worktrees": {
            "enabled": True,
            "baseBranchMode": "fixed",
            "baseBranch": "develop"
        }
    }
    manifest_path.write_text(json.dumps(manifest_data))

    # Initialize config - PathResolver will naturally resolve to isolated_project_env
    config = SessionConfig(repo_root=root)

    # Act
    wt_config = config.get_worktree_config()

    # Assert
    assert wt_config["enabled"] is True
    assert wt_config["baseBranch"] == "develop"
    assert wt_config["baseBranchMode"] == "fixed"

def test_get_worktree_config_handles_malformed_json(isolated_project_env):
    """Test resilience against bad JSON in manifest."""
    root = isolated_project_env
    config_dir = get_project_config_dir(root)
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config_dir / "manifest.json"

    # Write invalid JSON
    manifest_path.write_text("{invalid json")

    # Initialize config - PathResolver will naturally resolve to isolated_project_env
    config = SessionConfig(repo_root=root)

    # Should not raise, should return defaults
    wt_config = config.get_worktree_config()
    assert wt_config["enabled"] is True # default
    assert wt_config["baseBranchMode"] == "current" # default
    assert wt_config["baseBranch"] is None # default
