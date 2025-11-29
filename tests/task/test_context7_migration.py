import pytest
import json
import yaml
from pathlib import Path
from edison.core.qa.context.context7 import load_validator_config

def test_load_validator_config_json(isolated_project_env):
    """Test loading validator config from JSON."""
    root = isolated_project_env

    # Setup .edison/validators/config.json
    config_dir = root / ".edison" / "validators"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"

    data = {"postTrainingPackages": {"react": {"triggers": ["*.tsx"]}}}
    config_path.write_text(json.dumps(data))

    # PathResolver will naturally resolve to isolated_project_env
    config = load_validator_config()
    assert config["postTrainingPackages"]["react"]["triggers"] == ["*.tsx"]

def test_load_validator_config_yaml(isolated_project_env):
    """Test loading validator config from YAML (regression check)."""
    root = isolated_project_env

    # Setup .edison/config/validators.yml
    config_dir = root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "validators.yml"

    data = {"postTrainingPackages": {"react": {"triggers": ["*.tsx"]}}}
    config_path.write_text(yaml.dump(data))

    # PathResolver will naturally resolve to isolated_project_env
    config = load_validator_config()
    assert config["postTrainingPackages"]["react"]["triggers"] == ["*.tsx"]

def test_load_validator_config_malformed_json(isolated_project_env):
    """Test loading malformed JSON config."""
    root = isolated_project_env

    config_dir = root / ".edison" / "validators"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"

    config_path.write_text("{invalid json")

    # PathResolver will naturally resolve to isolated_project_env
    # Should return empty dict on error (default behavior)
    config = load_validator_config()
    assert config == {}
