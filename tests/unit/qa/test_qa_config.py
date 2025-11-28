"""QA configuration must be YAML-driven with class-based API.

This test asserts that QAConfig class provides typed access to delegation
and validation configuration sections from YAML files placed under
``.edison/core/config``. The QAConfig helper should follow the same pattern
as TaskConfig and SessionConfig.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


@pytest.mark.qa
def test_qa_config_class_provides_delegation_config(tmp_path: Path, monkeypatch):
    """QAConfig must provide get_delegation_config() method."""
    repo = tmp_path
    (repo / ".git").mkdir()

    # Project config placed under .edison/config (not .edison/core/config)
    config_dir = repo / ".edison" / "config"
    _write_yaml(
        config_dir / "defaults.yaml",
        {
            "delegation": {
                "taskTypeRules": {
                    "ui-component": {
                        "preferredModel": "claude",
                        "preferredZenRole": "component-builder-nextjs",
                    }
                },
                "filePatternRules": {},
                "subAgentDefaults": {},
            },
            "orchestration": {
                "maxConcurrentAgents": 5,
            },
        },
    )

    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    from edison.core.config.domains.qa import QAConfig

    cfg = QAConfig(repo_root=repo)

    delegation = cfg.get_delegation_config()
    assert isinstance(delegation, dict)
    assert "taskTypeRules" in delegation
    assert delegation["taskTypeRules"]["ui-component"]["preferredModel"] == "claude"


@pytest.mark.qa
def test_qa_config_class_provides_validation_config(tmp_path: Path, monkeypatch):
    """QAConfig must provide get_validation_config() method."""
    repo = tmp_path
    (repo / ".git").mkdir()

    # Project config placed under .edison/config (not .edison/core/config)
    config_dir = repo / ".edison" / "config"
    _write_yaml(
        config_dir / "defaults.yaml",
        {
            "validation": {
                "dimensions": {
                    "functionality": 30,
                    "reliability": 25,
                    "security": 20,
                    "maintainability": 15,
                    "performance": 10,
                },
                "roster": {
                    "global": [
                        {
                            "id": "global-codex",
                            "name": "Codex Global",
                            "model": "codex",
                        }
                    ],
                },
            },
        },
    )

    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    from edison.core.config.domains.qa import QAConfig

    cfg = QAConfig(repo_root=repo)

    validation = cfg.get_validation_config()
    assert isinstance(validation, dict)
    assert "dimensions" in validation
    assert validation["dimensions"]["functionality"] == 30
    assert validation["dimensions"]["reliability"] == 25
    assert validation["dimensions"]["security"] == 20
    assert "roster" in validation


@pytest.mark.qa
def test_qa_config_class_provides_max_concurrent_validators(tmp_path: Path, monkeypatch):
    """QAConfig must provide max_concurrent_validators() method."""
    repo = tmp_path
    (repo / ".git").mkdir()

    # Project config placed under .edison/config (not .edison/core/config)
    config_dir = repo / ".edison" / "config"
    _write_yaml(
        config_dir / "defaults.yaml",
        {
            "orchestration": {
                "maxConcurrentAgents": 3,
            },
        },
    )

    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    from edison.core.config.domains.qa import QAConfig

    cfg = QAConfig(repo_root=repo)

    max_concurrent = cfg.max_concurrent_validators()
    assert isinstance(max_concurrent, int)
    assert max_concurrent == 3


@pytest.mark.qa
def test_qa_config_class_falls_back_to_bundled_defaults(tmp_path: Path, monkeypatch):
    """QAConfig falls back to bundled defaults when project config is empty.

    The system is designed to always provide sensible defaults from bundled config,
    so even with an empty project config, maxConcurrentAgents should be available.
    This test verifies that bundled defaults are properly loaded.
    """
    repo = tmp_path
    (repo / ".git").mkdir()

    # Project config placed under .edison/config (not .edison/core/config)
    config_dir = repo / ".edison" / "config"
    _write_yaml(
        config_dir / "defaults.yaml",
        {
            # Empty config - should fall back to bundled defaults
        },
    )

    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    from edison.core.config.domains.qa import QAConfig

    cfg = QAConfig(repo_root=repo)

    # Should get value from bundled defaults (currently 5 in defaults.yaml)
    max_concurrent = cfg.max_concurrent_validators()
    assert isinstance(max_concurrent, int)
    assert max_concurrent > 0  # Should have a sensible default
