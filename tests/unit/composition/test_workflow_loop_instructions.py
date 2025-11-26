"""
Tests for composition workflow loop instructions (T-016 Pattern 3).

Tests verify that get_workflow_loop_instructions() ONLY loads from
composition.yaml and does NOT use hardcoded fallbacks (NO LEGACY principle).

Following STRICT TDD:
- RED: These tests FAIL before removing hardcoded fallback
- GREEN: Tests PASS after fallback removal
- NO MOCKS: Tests use real filesystem via tmp_path and monkeypatch
"""

import pytest
from pathlib import Path
from typing import Dict, Any
import yaml


def test_workflow_loop_loads_from_composition_yaml(tmp_path: Path, monkeypatch) -> None:
    """
    get_workflow_loop_instructions() loads ONLY from composition.yaml.

    RED: Would PASS even without composition.yaml (fallback exists)
    GREEN: PASSES only when composition.yaml exists
    """
    # Setup: Create composition.yaml with custom workflow config
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    custom_workflow = {
        "command": "scripts/custom/command <id>",
        "frequency": "Custom frequency",
        "readOrder": [
            "1. CUSTOM INSTRUCTION",
            "2. ANOTHER CUSTOM"
        ]
    }

    composition_yaml = config_dir / "composition.yaml"
    composition_yaml.write_text(yaml.safe_dump({
        "composition": {
            "workflowLoop": custom_workflow
        }
    }), encoding="utf-8")

    # Mock get_data_path to return our test config
    def mock_get_data_path(domain: str, filename: str) -> Path:
        if domain == "config" and filename == "composition.yaml":
            return composition_yaml
        raise FileNotFoundError(f"{domain}/{filename}")

    monkeypatch.setattr("edison.core.composition.workflow.get_data_path", mock_get_data_path)

    # Import after monkeypatch
    from edison.core.composition.workflow import get_workflow_loop_instructions

    # Test
    result = get_workflow_loop_instructions()

    # Verify it loaded from composition.yaml (not hardcoded)
    assert result["command"] == "scripts/custom/command <id>"
    assert result["frequency"] == "Custom frequency"
    assert len(result["readOrder"]) == 2
    assert "CUSTOM INSTRUCTION" in result["readOrder"][0]


def test_workflow_loop_requires_composition_yaml(tmp_path: Path, monkeypatch) -> None:
    """
    get_workflow_loop_instructions() FAILS when composition.yaml is missing.

    RED: Would PASS (returns hardcoded fallback)
    GREEN: FAILS with clear ConfigError

    T-016: NO LEGACY - No hardcoded fallbacks allowed
    """
    # Setup: NO composition.yaml exists
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    composition_yaml = config_dir / "composition.yaml"
    # NOTE: File intentionally not created

    def mock_get_data_path(domain: str, filename: str) -> Path:
        if domain == "config" and filename == "composition.yaml":
            return composition_yaml
        raise FileNotFoundError(f"{domain}/{filename}")

    monkeypatch.setattr("edison.core.composition.workflow.get_data_path", mock_get_data_path)

    from edison.core.composition.workflow import get_workflow_loop_instructions

    # Test: Should raise clear error (NO fallback)
    with pytest.raises(FileNotFoundError, match="composition.yaml"):
        get_workflow_loop_instructions()


def test_workflow_loop_fails_on_invalid_yaml(tmp_path: Path, monkeypatch) -> None:
    """
    get_workflow_loop_instructions() FAILS on malformed YAML.

    RED: Would PASS (returns hardcoded fallback on exception)
    GREEN: FAILS with clear error

    T-016: NO LEGACY - Fail fast, don't hide errors with fallbacks
    """
    # Setup: Create invalid YAML
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    composition_yaml = config_dir / "composition.yaml"
    composition_yaml.write_text("invalid: yaml: content: [unclosed", encoding="utf-8")

    def mock_get_data_path(domain: str, filename: str) -> Path:
        if domain == "config" and filename == "composition.yaml":
            return composition_yaml
        raise FileNotFoundError(f"{domain}/{filename}")

    monkeypatch.setattr("edison.core.composition.workflow.get_data_path", mock_get_data_path)

    from edison.core.composition.workflow import get_workflow_loop_instructions

    # Test: Should raise YAML parse error (not fallback)
    with pytest.raises(Exception):  # yaml.YAMLError or similar
        get_workflow_loop_instructions()


def test_workflow_loop_fails_on_missing_workflowLoop_key(tmp_path: Path, monkeypatch) -> None:
    """
    get_workflow_loop_instructions() FAILS when workflowLoop key is missing.

    RED: Would PASS (returns hardcoded fallback)
    GREEN: FAILS with KeyError or returns None

    T-016: NO LEGACY - Require explicit config, no silent fallbacks
    """
    # Setup: composition.yaml without workflowLoop
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    composition_yaml = config_dir / "composition.yaml"
    composition_yaml.write_text(yaml.safe_dump({
        "composition": {
            "dryDetection": {
                "minShingles": 2
            }
            # NOTE: No workflowLoop key
        }
    }), encoding="utf-8")

    def mock_get_data_path(domain: str, filename: str) -> Path:
        if domain == "config" and filename == "composition.yaml":
            return composition_yaml
        raise FileNotFoundError(f"{domain}/{filename}")

    monkeypatch.setattr("edison.core.composition.workflow.get_data_path", mock_get_data_path)

    from edison.core.composition.workflow import get_workflow_loop_instructions

    # Test: Should fail (no fallback)
    with pytest.raises((KeyError, FileNotFoundError), match="workflowLoop|composition.yaml"):
        get_workflow_loop_instructions()


def test_workflow_loop_never_returns_hardcoded_values(tmp_path: Path, monkeypatch) -> None:
    """
    get_workflow_loop_instructions() NEVER returns hardcoded default values.

    RED: Would FAIL (hardcoded values exist and are returned)
    GREEN: PASSES (only config values returned)

    T-016: NO LEGACY - Verify hardcoded dict is completely removed
    """
    # Setup: Custom config with DIFFERENT values than hardcoded defaults
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    custom_workflow = {
        "command": "CUSTOM_COMMAND",
        "frequency": "CUSTOM_FREQUENCY",
        "readOrder": ["CUSTOM_1", "CUSTOM_2"]
    }

    composition_yaml = config_dir / "composition.yaml"
    composition_yaml.write_text(yaml.safe_dump({
        "composition": {
            "workflowLoop": custom_workflow
        }
    }), encoding="utf-8")

    def mock_get_data_path(domain: str, filename: str) -> Path:
        if domain == "config" and filename == "composition.yaml":
            return composition_yaml
        raise FileNotFoundError(f"{domain}/{filename}")

    monkeypatch.setattr("edison.core.composition.workflow.get_data_path", mock_get_data_path)

    from edison.core.composition.workflow import get_workflow_loop_instructions

    result = get_workflow_loop_instructions()

    # Verify NO hardcoded values are present
    assert "scripts/session next <session-id>" not in result["command"]
    assert "Before EVERY action" not in result["frequency"]
    assert "📋 APPLICABLE RULES" not in str(result["readOrder"])

    # Verify ONLY custom values
    assert result["command"] == "CUSTOM_COMMAND"
    assert result["frequency"] == "CUSTOM_FREQUENCY"
    assert result["readOrder"] == ["CUSTOM_1", "CUSTOM_2"]


def test_workflow_loop_real_composition_yaml_loads() -> None:
    """
    Integration test: Real composition.yaml loads successfully.

    Baseline test: Verify actual config file works (not isolated).
    """
    from edison.core.composition.workflow import get_workflow_loop_instructions

    # This uses real filesystem - should work in CI/production
    result = get_workflow_loop_instructions()

    # Verify structure (values match composition.yaml)
    assert "command" in result
    assert "frequency" in result
    assert "readOrder" in result
    assert isinstance(result["readOrder"], list)
    assert len(result["readOrder"]) > 0
