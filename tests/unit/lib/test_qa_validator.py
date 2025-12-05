"""Tests for QA validator system.

Tests the new engine-based validator system and delegation hints.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from edison.core.task import TaskQAWorkflow
from edison.core.qa.engines import EngineRegistry
from edison.core.session.delegation import simple_delegation_hint
from tests.helpers.paths import get_repo_root


def test_simple_delegation_hint_uses_task_type_rules(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    simple_delegation_hint should respect taskTypeRules when task doc declares a type.

    This tests the delegation logic for task implementation suggestions.
    """
    # isolated_project_env fixture already sets AGENTS_PROJECT_ROOT and resets caches

    task_id = "9000-delegation-ui-component"
    # Create a real task file via TaskQAWorkflow
    workflow = TaskQAWorkflow(project_root=isolated_project_env)
    workflow.create_task(task_id, "Delegation smoke test", create_qa=False)
    task_repo = workflow._task_repo
    task_path = task_repo._find_entity_path(task_id)

    # Append a minimal Task Type stanza expected by the parser
    original = task_path.read_text(encoding="utf-8")
    task_path.write_text(original + "\nTask Type: ui-component\n", encoding="utf-8")

    # Minimal delegation snippet with a ui-component rule
    delegation_cfg: dict[str, Any] = {
        "taskTypeRules": {
            "ui-component": {
                "preferredModel": "claude",
                "preferredZenRole": "component-builder-nextjs",
            }
        },
        "filePatternRules": {},
        "subAgentDefaults": {},
    }

    hint = simple_delegation_hint(task_id, delegation_cfg=delegation_cfg)
    assert hint is not None, "expected a delegation hint for ui-component task"
    assert hint.get("model") == "claude"
    assert hint.get("zenRole") == "component-builder-nextjs"


def test_engine_registry_build_execution_roster(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    EngineRegistry.build_execution_roster should categorize validators.

    This tests the new engine-based validator roster building.
    """
    # isolated_project_env fixture already sets AGENTS_PROJECT_ROOT and resets caches

    # Create a simple task
    task_id = "9001-validator-roster"
    workflow = TaskQAWorkflow(project_root=isolated_project_env)
    workflow.create_task(task_id, "Validator roster smoke test", create_qa=False)

    # Create engine registry
    registry = EngineRegistry(project_root=isolated_project_env)

    # Build roster
    roster = registry.build_execution_roster(task_id, session_id=None)

    # Check roster structure
    assert "taskId" in roster
    assert roster["taskId"] == task_id
    assert "alwaysRequired" in roster
    assert "triggeredBlocking" in roster
    assert "triggeredOptional" in roster
    assert "totalBlocking" in roster


def test_engine_registry_get_validator(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EngineRegistry should load validator configurations."""
    # Create engine registry
    registry = EngineRegistry(project_root=isolated_project_env)

    # List validators
    validators = registry.list_validators()
    assert isinstance(validators, list)

    # If we have validators configured, test get_validator
    if validators:
        first_validator = validators[0]
        config = registry.get_validator(first_validator)
        assert config is not None
        assert config.id == first_validator


def test_load_delegation_config_uses_yaml_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    qa.config.load_delegation_config should source data from YAML ConfigManager.

    The JSON delegation overlay under .agents/delegation/config.json only
    contains priority lists, while the core YAML config defines rich
    filePatternRules/taskTypeRules. This asserts YAML is used.
    """
    from edison.core.qa import config as qa_config
    from edison.core.config import ConfigManager

    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    repo_root = get_repo_root()
    cfg = ConfigManager(repo_root).load_config(validate=False)
    expected = cfg.get("delegation", {}) or {}

    loaded = qa_config.load_delegation_config(repo_root=repo_root)

    assert loaded == expected


def test_load_validation_config_uses_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """qa.config.load_validation_config should return the validation section from YAML."""
    from edison.core.qa import config as qa_config
    from edison.core.config import ConfigManager

    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    repo_root = get_repo_root()
    cfg = ConfigManager(repo_root).load_config(validate=False)
    expected = cfg.get("validation", {}) or {}

    loaded = qa_config.load_validation_config(repo_root=repo_root)

    assert loaded == expected


def test_qa_config_get_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    """QAConfig.get_engines() should return engine configurations."""
    from edison.core.config.domains.qa import QAConfig

    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    repo_root = get_repo_root()

    config = QAConfig(repo_root=repo_root)
    engines = config.get_engines()

    assert isinstance(engines, dict)
    # Check for expected engine keys (from new validators.yaml)
    if engines:  # Only if engines are configured
        # Engine IDs should be strings
        for engine_id in engines:
            assert isinstance(engine_id, str)


def test_qa_config_get_validators(monkeypatch: pytest.MonkeyPatch) -> None:
    """QAConfig.get_validators() should return validator configurations."""
    from edison.core.config.domains.qa import QAConfig

    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    repo_root = get_repo_root()

    config = QAConfig(repo_root=repo_root)
    validators = config.get_validators()

    assert isinstance(validators, dict)
    # Validators should have expected structure
    for validator_id, validator_cfg in validators.items():
        assert isinstance(validator_id, str)
        assert isinstance(validator_cfg, dict)
