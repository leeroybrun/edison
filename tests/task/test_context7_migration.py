import pytest
import json
import yaml
from pathlib import Path
from edison.core.qa.context7 import load_validator_config
from edison.core.utils.paths.resolver import PathResolver

def test_load_validator_config_json(tmp_path, monkeypatch):
    """Test loading validator config from JSON."""
    root = tmp_path / "project"
    root.mkdir()
    
    # Setup .edison/validators/config.json
    config_dir = root / ".edison" / "validators"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"
    
    data = {"postTrainingPackages": {"react": {"triggers": ["*.tsx"]}}}
    config_path.write_text(json.dumps(data))
    
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: root)
    
    config = load_validator_config()
    assert config["postTrainingPackages"]["react"]["triggers"] == ["*.tsx"]

def test_load_validator_config_yaml(tmp_path, monkeypatch):
    """Test loading validator config from YAML (regression check)."""
    root = tmp_path / "project"
    root.mkdir()
    
    # Setup .edison/config/validators.yml
    config_dir = root / ".edison" / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "validators.yml"
    
    data = {"postTrainingPackages": {"react": {"triggers": ["*.tsx"]}}}
    config_path.write_text(yaml.dump(data))
    
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: root)
    
    config = load_validator_config()
    assert config["postTrainingPackages"]["react"]["triggers"] == ["*.tsx"]

def test_load_validator_config_malformed_json(tmp_path, monkeypatch):
    """Test loading malformed JSON config."""
    root = tmp_path / "project"
    root.mkdir()
    
    config_dir = root / ".edison" / "validators"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"
    
    config_path.write_text("{invalid json")
    
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: root)
    
    # Should return empty dict on error (default behavior)
    config = load_validator_config()
    assert config == {}
