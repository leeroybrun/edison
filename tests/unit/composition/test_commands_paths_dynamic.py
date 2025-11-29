import pytest
from pathlib import Path
from edison.core.composition.ide.commands import CommandComposer
from edison.core.utils.paths.project import get_project_config_dir

def test_command_composer_uses_dynamic_project_dir(tmp_path):
    """Test that CommandComposer resolves project_dir dynamically."""
    # Arrange
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".edison" / "core").mkdir(parents=True)
    
    # Act
    composer = CommandComposer(repo_root=repo)
    
    # Assert
    # Should resolve to repo/.edison
    expected = get_project_config_dir(repo)
    assert composer.project_dir == expected
    assert composer.project_dir.name != ".agents"
    assert composer.project_dir.name == ".edison"

def test_command_composer_respects_env_var(tmp_path, monkeypatch):
    """Test that CommandComposer respects EDISON_paths__project_config_dir."""
    # Arrange
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".edison" / "core").mkdir(parents=True)
    custom_dir = repo / ".custom_config"
    custom_dir.mkdir()
    
    monkeypatch.setenv("EDISON_paths__project_config_dir", ".custom_config")
    
    # Act
    composer = CommandComposer(repo_root=repo)
    
    # Assert
    assert composer.project_dir == custom_dir
