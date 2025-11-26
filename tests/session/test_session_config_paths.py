
import os
import pytest
import json
from pathlib import Path
from edison.core.session.config import SessionConfig
from edison.core.paths.project import get_project_config_dir

class TestSessionConfigPaths:
    
    def test_manifest_path_respects_project_config_dir(self, tmp_path, monkeypatch):
        """Verify manifest is loaded from resolved config dir, not hardcoded .agents"""
        
        # Setup structure
        # repo_root/
        #   .edison/
        #     manifest.json  (contains specific override)
        #   .agents/
        #     manifest.json  (contains trap override)
        
        repo_root = tmp_path
        edison_dir = repo_root / ".edison"
        edison_dir.mkdir()
        
        agents_dir = repo_root / ".agents"
        agents_dir.mkdir()
        
        # 1. Create manifest in .edison (Desired)
        edison_manifest = {
            "worktrees": {
                "branchPrefix": "edison-prefix/"
            }
        }
        (edison_dir / "manifest.json").write_text(json.dumps(edison_manifest))
        
        # 2. Create manifest in .agents (Trap - legacy)
        agents_manifest = {
            "worktrees": {
                "branchPrefix": "legacy-prefix/"
            }
        }
        (agents_dir / "manifest.json").write_text(json.dumps(agents_manifest))
        
        # 3. Initialize Config (no patching needed)
        
        # 4. Initialize Config
        config = SessionConfig(repo_root=repo_root)
        wt_config = config.get_worktree_config()
        
        # 5. Assert - Should find the one in .edison, NOT .agents
        # This will FAIL if code is still looking at .agents
        assert wt_config["branchPrefix"] == "edison-prefix/"

    def test_manifest_path_respects_env_var_override(self, tmp_path, monkeypatch):
        """Verify manifest follows EDISON_paths__project_config_dir override"""
        
        repo_root = tmp_path
        custom_config_dir = repo_root / ".custom-config"
        custom_config_dir.mkdir()
        
        # Create manifest in custom dir
        custom_manifest = {
            "worktrees": {
                "branchPrefix": "custom-prefix/"
            }
        }
        (custom_config_dir / "manifest.json").write_text(json.dumps(custom_manifest))
        
        # Set env var to point to custom dir
        monkeypatch.setenv("EDISON_paths__project_config_dir", str(custom_config_dir))

        
        # Initialize Config
        config = SessionConfig(repo_root=repo_root)
        wt_config = config.get_worktree_config()
        
        assert wt_config["branchPrefix"] == "custom-prefix/"

