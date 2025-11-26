import pytest
from pathlib import Path
from edison.core.composition import CompositionEngine
from edison.core.paths.project import get_project_config_dir

def test_composition_engine_init_no_fallback_to_agents(tmp_path):
    """
    Test that CompositionEngine uses default_project_dir even if 
    conditions for legacy fallback are met.
    """
    repo_root = tmp_path
    
    # Setup conditions that trigger the legacy fallback in current code:
    # 1. repo_root / ".edison" / "core" exists
    (repo_root / ".edison" / "core").mkdir(parents=True)
    
    # 2. default_project_dir / "config" does NOT exist
    # (default is .edison, so .edison/config does not exist yet)
    
    # 3. alt_project_dir (.agents) exists
    (repo_root / ".agents").mkdir()
    
    # Initialize Engine
    engine = CompositionEngine(repo_root=repo_root)
    
    # Assert
    # Current code sets self.project_dir to repo_root / ".agents"
    # We want it to be get_project_config_dir(repo_root) -> repo_root / ".edison"
    
    expected_dir = get_project_config_dir(repo_root)
    assert engine.project_dir == expected_dir, \
        f"Project dir should be {expected_dir}, but was {engine.project_dir}"
    assert engine.project_dir.name == ".edison"
    assert engine.project_dir.name != ".agents"
