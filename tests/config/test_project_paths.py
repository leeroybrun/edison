# tests/config/test_project_paths.py
import os
from pathlib import Path
import pytest
import yaml

from edison.core.paths.project import (
    DEFAULT_PROJECT_CONFIG_PRIMARY,
    _resolve_project_dir_from_configs,
    get_project_config_dir,
)


@pytest.fixture
def tmp_repo_root(tmp_path: Path):
    """Provides a temporary repository root for testing."""
    return tmp_path


@pytest.fixture(autouse=True)
def clean_env():
    """Cleans up EDISON_paths__project_config_dir env var before and after tests."""
    original_env_var = os.environ.get("EDISON_paths__project_config_dir")
    if "EDISON_paths__project_config_dir" in os.environ:
        del os.environ["EDISON_paths__project_config_dir"]
    yield
    if original_env_var is not None:
        os.environ["EDISON_paths__project_config_dir"] = original_env_var
    else:
        if "EDISON_paths__project_config_dir" in os.environ:
            del os.environ["EDISON_paths__project_config_dir"]


def test_get_project_config_dir_no_config_defaults_to_edison(tmp_repo_root: Path):
    """
    RED PHASE: Test that get_project_config_dir defaults to .edison when no config exists.
    This test is expected to FAIL with the current implementation.
    """
    expected_dir = tmp_repo_root / DEFAULT_PROJECT_CONFIG_PRIMARY
    actual_dir = get_project_config_dir(tmp_repo_root, create=False)
    assert actual_dir == expected_dir


def test_resolve_project_dir_from_configs_no_config_defaults_to_primary(tmp_repo_root: Path):
    """
    RED PHASE: Test that _resolve_project_dir_from_configs defaults to DEFAULT_PROJECT_CONFIG_PRIMARY
    when no config or env var is set. This test is expected to FAIL.
    """
    expected_name = DEFAULT_PROJECT_CONFIG_PRIMARY
    actual_name = _resolve_project_dir_from_configs(tmp_repo_root)
    assert actual_name == expected_name


def test_get_project_config_dir_yaml_config_respected(tmp_repo_root: Path):
    """
    RED PHASE: Test that paths.project_config_dir from a YAML config in .edison/config is respected.
    This test is expected to FAIL or pass depending on the exact implementation details of _resolve_project_dir_from_configs
    and if .agents config overrides it. This will verify if .edison is truly preferred.
    """
    config_dir = tmp_repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "test.yaml"
    
    custom_project_dir_name = ".my_custom_project"
    with open(config_file, "w") as f:
        yaml.dump({"paths": {"project_config_dir": custom_project_dir_name}}, f)

    expected_dir = tmp_repo_root / custom_project_dir_name
    actual_dir = get_project_config_dir(tmp_repo_root, create=False)
    assert actual_dir == expected_dir


def test_get_project_config_dir_env_var_overrides_yaml(tmp_repo_root: Path):
    """
    RED PHASE: Test that EDISON_paths__project_config_dir environment variable overrides YAML config.
    This test is expected to FAIL if env var handling is incorrect or if .agents fallback happens even with env var.
    """
    # Create YAML config
    config_dir = tmp_repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "test.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"paths": {"project_config_dir": ".from_yaml"}}, f)

    # Set environment variable
    env_override_name = ".from_env"
    os.environ["EDISON_paths__project_config_dir"] = env_override_name

    expected_dir = tmp_repo_root / env_override_name
    actual_dir = get_project_config_dir(tmp_repo_root, create=False)
    assert actual_dir == expected_dir


def test_get_project_config_dir_no_agents_fallback_with_edison_dir_exists(tmp_repo_root: Path):
    """
    RED PHASE: Test that if an .edison directory exists (even if empty), there's no fallback to .agents.
    This test is expected to FAIL, as the current implementation might still consider .agents if .edison is empty
    or if other logic prioritizes it.
    """
    # Create an empty .edison directory
    (tmp_repo_root / DEFAULT_PROJECT_CONFIG_PRIMARY).mkdir()
    
    # Create a legacy .agents directory with some config that would normally be picked up
    agents_config_dir = tmp_repo_root / ".agents" / "config"
    agents_config_dir.mkdir(parents=True)
    agents_config_file = agents_config_dir / "some_config.yaml"
    with open(agents_config_file, "w") as f:
        yaml.dump({"paths": {"project_config_dir": ".legacy_agents_config"}}, f)

    expected_dir = tmp_repo_root / DEFAULT_PROJECT_CONFIG_PRIMARY
    actual_dir = get_project_config_dir(tmp_repo_root, create=False)
    assert actual_dir == expected_dir
