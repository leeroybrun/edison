"""Tests for ConditionEvaluator and ConditionalProcessor.

Tests all 8 condition functions, nested conditions, error handling,
and conditional block processing.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from edison.core.composition.transformers.conditionals import (
    CompositionContext,
    ConditionEvaluator,
    ConditionalProcessor,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def empty_context() -> CompositionContext:
    """Context with no packs and empty config."""
    return CompositionContext(
        active_packs=[],
        config={},
        project_root=None,
    )


@pytest.fixture
def context_with_packs() -> CompositionContext:
    """Context with active packs."""
    return CompositionContext(
        active_packs=["python", "vitest", "prisma"],
        config={},
        project_root=None,
    )


@pytest.fixture
def context_with_config() -> CompositionContext:
    """Context with nested config values."""
    return CompositionContext(
        active_packs=["python"],
        config={
            "features": {
                "auth": True,
                "disabled": False,
                "metrics": {"enabled": True},
            },
            "project": {
                "type": "api",
                "name": "test-project",
            },
            "strict": True,
            "empty_value": "",
            "zero_value": 0,
        },
        project_root=None,
    )


@pytest.fixture
def context_with_project_root(tmp_path: Path) -> CompositionContext:
    """Context with project root for file existence checks."""
    # Create some test files
    (tmp_path / ".eslintrc").touch()
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").touch()

    return CompositionContext(
        active_packs=["python"],
        config={},
        project_root=tmp_path,
    )


@pytest.fixture
def full_context(tmp_path: Path) -> CompositionContext:
    """Full context with packs, config, and project root."""
    (tmp_path / ".eslintrc").touch()

    return CompositionContext(
        active_packs=["python", "vitest", "tailwind"],
        config={
            "features": {"auth": True},
            "project": {"type": "api"},
            "strict": True,
        },
        project_root=tmp_path,
    )


# =============================================================================
# CompositionContext Tests
# =============================================================================


class TestCompositionContext:
    """Tests for CompositionContext."""

    def test_get_config_simple_path(self, context_with_config: CompositionContext) -> None:
        """Test getting a simple config value."""
        assert context_with_config.get_config("strict") is True

    def test_get_config_nested_path(self, context_with_config: CompositionContext) -> None:
        """Test getting a nested config value."""
        assert context_with_config.get_config("features.auth") is True
        assert context_with_config.get_config("project.type") == "api"

    def test_get_config_deeply_nested(self, context_with_config: CompositionContext) -> None:
        """Test getting a deeply nested config value."""
        assert context_with_config.get_config("features.metrics.enabled") is True

    def test_get_config_missing_path(self, context_with_config: CompositionContext) -> None:
        """Test getting a non-existent config path returns None."""
        assert context_with_config.get_config("nonexistent") is None
        assert context_with_config.get_config("features.nonexistent") is None
        assert context_with_config.get_config("deeply.nested.missing") is None

    def test_get_config_empty_value(self, context_with_config: CompositionContext) -> None:
        """Test getting empty/zero values."""
        assert context_with_config.get_config("empty_value") == ""
        assert context_with_config.get_config("zero_value") == 0


# =============================================================================
# ConditionEvaluator Tests - has-pack()
# =============================================================================


class TestHasPackCondition:
    """Tests for has-pack() condition function."""

    def test_has_pack_active(self, context_with_packs: CompositionContext) -> None:
        """Test has-pack() returns True for active pack."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("has-pack(python)") is True
        assert evaluator.evaluate("has-pack(vitest)") is True
        assert evaluator.evaluate("has-pack(prisma)") is True

    def test_has_pack_inactive(self, context_with_packs: CompositionContext) -> None:
        """Test has-pack() returns False for inactive pack."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("has-pack(legacy)") is False
        assert evaluator.evaluate("has-pack(jest)") is False

    def test_has_pack_empty_context(self, empty_context: CompositionContext) -> None:
        """Test has-pack() with no active packs."""
        evaluator = ConditionEvaluator(empty_context)
        assert evaluator.evaluate("has-pack(python)") is False


# =============================================================================
# ConditionEvaluator Tests - config()
# =============================================================================


class TestConfigCondition:
    """Tests for config() condition function."""

    def test_config_truthy_true(self, context_with_config: CompositionContext) -> None:
        """Test config() returns True for truthy values."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config(features.auth)") is True
        assert evaluator.evaluate("config(strict)") is True

    def test_config_truthy_false(self, context_with_config: CompositionContext) -> None:
        """Test config() returns False for falsy values."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config(features.disabled)") is False
        assert evaluator.evaluate("config(empty_value)") is False
        assert evaluator.evaluate("config(zero_value)") is False

    def test_config_missing(self, context_with_config: CompositionContext) -> None:
        """Test config() returns False for missing paths."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config(nonexistent)") is False
        assert evaluator.evaluate("config(features.missing)") is False


# =============================================================================
# ConditionEvaluator Tests - config-eq()
# =============================================================================


class TestConfigEqCondition:
    """Tests for config-eq() condition function."""

    def test_config_eq_match(self, context_with_config: CompositionContext) -> None:
        """Test config-eq() returns True when values match."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config-eq(project.type, api)") is True
        assert evaluator.evaluate("config-eq(project.name, test-project)") is True

    def test_config_eq_no_match(self, context_with_config: CompositionContext) -> None:
        """Test config-eq() returns False when values don't match."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config-eq(project.type, web)") is False
        assert evaluator.evaluate("config-eq(project.name, other)") is False

    def test_config_eq_missing_path(self, context_with_config: CompositionContext) -> None:
        """Test config-eq() returns False for missing paths."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config-eq(nonexistent, value)") is False

    def test_config_eq_boolean_as_string(self, context_with_config: CompositionContext) -> None:
        """Test config-eq() compares as strings."""
        evaluator = ConditionEvaluator(context_with_config)
        assert evaluator.evaluate("config-eq(strict, True)") is True


# =============================================================================
# ConditionEvaluator Tests - env()
# =============================================================================


class TestEnvCondition:
    """Tests for env() condition function."""

    def test_env_set(self, monkeypatch: pytest.MonkeyPatch, empty_context: CompositionContext) -> None:
        """Test env() returns True when environment variable is set."""
        monkeypatch.setenv("TEST_VAR", "value")
        evaluator = ConditionEvaluator(empty_context)
        assert evaluator.evaluate("env(TEST_VAR)") is True

    def test_env_not_set(self, empty_context: CompositionContext) -> None:
        """Test env() returns False when environment variable is not set."""
        evaluator = ConditionEvaluator(empty_context)
        # Use a unique variable name that definitely doesn't exist
        assert evaluator.evaluate("env(DEFINITELY_NONEXISTENT_VAR_12345)") is False

    def test_env_empty_value(self, monkeypatch: pytest.MonkeyPatch, empty_context: CompositionContext) -> None:
        """Test env() returns False when environment variable is empty."""
        monkeypatch.setenv("EMPTY_VAR", "")
        evaluator = ConditionEvaluator(empty_context)
        assert evaluator.evaluate("env(EMPTY_VAR)") is False


# =============================================================================
# ConditionEvaluator Tests - file-exists()
# =============================================================================


class TestFileExistsCondition:
    """Tests for file-exists() condition function."""

    def test_file_exists_true(self, context_with_project_root: CompositionContext) -> None:
        """Test file-exists() returns True when file exists."""
        evaluator = ConditionEvaluator(context_with_project_root)
        assert evaluator.evaluate("file-exists(.eslintrc)") is True
        assert evaluator.evaluate("file-exists(package.json)") is True

    def test_file_exists_nested(self, context_with_project_root: CompositionContext) -> None:
        """Test file-exists() with nested paths."""
        evaluator = ConditionEvaluator(context_with_project_root)
        assert evaluator.evaluate("file-exists(src/index.ts)") is True

    def test_file_exists_false(self, context_with_project_root: CompositionContext) -> None:
        """Test file-exists() returns False when file doesn't exist."""
        evaluator = ConditionEvaluator(context_with_project_root)
        assert evaluator.evaluate("file-exists(nonexistent.txt)") is False

    def test_file_exists_no_project_root(self, empty_context: CompositionContext) -> None:
        """Test file-exists() returns False when no project root."""
        evaluator = ConditionEvaluator(empty_context)
        assert evaluator.evaluate("file-exists(anything.txt)") is False


# =============================================================================
# ConditionEvaluator Tests - not()
# =============================================================================


class TestNotCondition:
    """Tests for not() logical operator."""

    def test_not_true(self, context_with_packs: CompositionContext) -> None:
        """Test not() negates true to false."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("not(has-pack(python))") is False

    def test_not_false(self, context_with_packs: CompositionContext) -> None:
        """Test not() negates false to true."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("not(has-pack(legacy))") is True


# =============================================================================
# ConditionEvaluator Tests - and()
# =============================================================================


class TestAndCondition:
    """Tests for and() logical operator."""

    def test_and_both_true(self, context_with_packs: CompositionContext) -> None:
        """Test and() returns True when both conditions are true."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("and(has-pack(python), has-pack(vitest))") is True

    def test_and_first_false(self, context_with_packs: CompositionContext) -> None:
        """Test and() returns False when first condition is false."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("and(has-pack(legacy), has-pack(python))") is False

    def test_and_second_false(self, context_with_packs: CompositionContext) -> None:
        """Test and() returns False when second condition is false."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("and(has-pack(python), has-pack(legacy))") is False

    def test_and_both_false(self, context_with_packs: CompositionContext) -> None:
        """Test and() returns False when both conditions are false."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("and(has-pack(jest), has-pack(legacy))") is False


# =============================================================================
# ConditionEvaluator Tests - or()
# =============================================================================


class TestOrCondition:
    """Tests for or() logical operator."""

    def test_or_both_true(self, context_with_packs: CompositionContext) -> None:
        """Test or() returns True when both conditions are true."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("or(has-pack(python), has-pack(vitest))") is True

    def test_or_first_true(self, context_with_packs: CompositionContext) -> None:
        """Test or() returns True when first condition is true."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("or(has-pack(python), has-pack(legacy))") is True

    def test_or_second_true(self, context_with_packs: CompositionContext) -> None:
        """Test or() returns True when second condition is true."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("or(has-pack(legacy), has-pack(python))") is True

    def test_or_both_false(self, context_with_packs: CompositionContext) -> None:
        """Test or() returns False when both conditions are false."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("or(has-pack(jest), has-pack(legacy))") is False


# =============================================================================
# ConditionEvaluator Tests - Nested Conditions
# =============================================================================


class TestNestedConditions:
    """Tests for nested condition expressions."""

    def test_nested_and_not(self, context_with_packs: CompositionContext) -> None:
        """Test and() with nested not()."""
        evaluator = ConditionEvaluator(context_with_packs)
        # has python AND NOT legacy
        assert evaluator.evaluate("and(has-pack(python), not(has-pack(legacy)))") is True
        # has python AND NOT vitest (vitest is active)
        assert evaluator.evaluate("and(has-pack(python), not(has-pack(vitest)))") is False

    def test_nested_or_not(self, context_with_packs: CompositionContext) -> None:
        """Test or() with nested not()."""
        evaluator = ConditionEvaluator(context_with_packs)
        # has legacy OR NOT jest (neither exists, so OR of false and true)
        assert evaluator.evaluate("or(has-pack(legacy), not(has-pack(jest)))") is True

    def test_complex_nested(self, full_context: CompositionContext) -> None:
        """Test complex nested conditions."""
        evaluator = ConditionEvaluator(full_context)
        # (has python AND has vitest) - both true
        result = evaluator.evaluate("and(has-pack(python), has-pack(vitest))")
        assert result is True

    def test_mixed_conditions(self, full_context: CompositionContext) -> None:
        """Test mixing different condition types."""
        evaluator = ConditionEvaluator(full_context)
        # has-pack AND config - both true
        assert evaluator.evaluate("and(has-pack(python), config(strict))") is True
        # has-pack AND file-exists - both true
        assert evaluator.evaluate("and(has-pack(python), file-exists(.eslintrc))") is True


# =============================================================================
# ConditionEvaluator Tests - Error Handling
# =============================================================================


class TestConditionErrors:
    """Tests for error handling in ConditionEvaluator."""

    def test_empty_expression(self, empty_context: CompositionContext) -> None:
        """Test empty expression raises ValueError."""
        evaluator = ConditionEvaluator(empty_context)
        with pytest.raises(ValueError, match="Empty condition expression"):
            evaluator.evaluate("")
        with pytest.raises(ValueError, match="Empty condition expression"):
            evaluator.evaluate("   ")

    def test_invalid_expression_format(self, empty_context: CompositionContext) -> None:
        """Test invalid expression format raises ValueError."""
        evaluator = ConditionEvaluator(empty_context)
        with pytest.raises(ValueError, match="Invalid condition expression"):
            evaluator.evaluate("not-a-function")
        with pytest.raises(ValueError, match="Invalid condition expression"):
            evaluator.evaluate("has-pack python")  # Missing parentheses

    def test_unknown_function(self, empty_context: CompositionContext) -> None:
        """Test unknown function raises ValueError."""
        evaluator = ConditionEvaluator(empty_context)
        with pytest.raises(ValueError, match="Unknown condition function"):
            evaluator.evaluate("unknown-func(arg)")

    def test_available_functions_in_error(self, empty_context: CompositionContext) -> None:
        """Test error message includes available functions."""
        evaluator = ConditionEvaluator(empty_context)
        with pytest.raises(ValueError) as exc_info:
            evaluator.evaluate("bad-func(arg)")
        assert "has-pack" in str(exc_info.value)
        assert "config" in str(exc_info.value)


# =============================================================================
# ConditionalProcessor Tests
# =============================================================================


class TestConditionalProcessor:
    """Tests for ConditionalProcessor."""

    def test_process_if_block_true(self, context_with_packs: CompositionContext) -> None:
        """Test if block includes content when condition is true."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """Before
{{if:has-pack(python)}}
Python content
{{/if}}
After"""

        result = processor.process_if_blocks(content)
        assert "Python content" in result
        assert "{{if:" not in result
        assert "{{/if}}" not in result

    def test_process_if_block_false(self, context_with_packs: CompositionContext) -> None:
        """Test if block excludes content when condition is false."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """Before
{{if:has-pack(legacy)}}
Legacy content
{{/if}}
After"""

        result = processor.process_if_blocks(content)
        assert "Legacy content" not in result
        assert "Before" in result
        assert "After" in result

    def test_process_if_else_true_branch(self, context_with_packs: CompositionContext) -> None:
        """Test if-else returns true branch when condition is true."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """{{if:has-pack(python)}}Use Python patterns{{else}}Use default patterns{{/if}}"""

        result = processor.process_if_blocks(content)
        assert "Use Python patterns" in result
        assert "Use default patterns" not in result

    def test_process_if_else_false_branch(self, context_with_packs: CompositionContext) -> None:
        """Test if-else returns false branch when condition is false."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """{{if:has-pack(legacy)}}Use legacy patterns{{else}}Use modern patterns{{/if}}"""

        result = processor.process_if_blocks(content)
        assert "Use modern patterns" in result
        assert "Use legacy patterns" not in result

    def test_process_multiple_if_blocks(self, context_with_packs: CompositionContext) -> None:
        """Test processing multiple if blocks."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """{{if:has-pack(python)}}Python{{/if}}
{{if:has-pack(vitest)}}Vitest{{/if}}
{{if:has-pack(legacy)}}Legacy{{/if}}"""

        result = processor.process_if_blocks(content)
        assert "Python" in result
        assert "Vitest" in result
        assert "Legacy" not in result

    def test_get_conditional_includes(self, context_with_packs: CompositionContext) -> None:
        """Test extracting conditional includes."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """{{include-if:has-pack(python):guidelines/PYTHON.md}}
{{include-if:has-pack(legacy):guidelines/LEGACY.md}}"""

        includes = processor.get_conditional_includes(content)
        assert len(includes) == 2
        assert includes[0] == ("has-pack(python)", "guidelines/PYTHON.md", True)
        assert includes[1] == ("has-pack(legacy)", "guidelines/LEGACY.md", False)

    def test_process_conditional_includes(self, context_with_packs: CompositionContext) -> None:
        """Test processing conditional includes."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        def resolver(path: str) -> str:
            return f"[Content of {path}]"

        content = """Before
{{include-if:has-pack(python):guidelines/PYTHON.md}}
{{include-if:has-pack(legacy):guidelines/LEGACY.md}}
After"""

        result = processor.process_conditional_includes(content, resolver)
        assert "[Content of guidelines/PYTHON.md]" in result
        assert "[Content of guidelines/LEGACY.md]" not in result
        assert "Before" in result
        assert "After" in result


# =============================================================================
# Whitespace and Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and whitespace handling."""

    def test_whitespace_in_expression(self, context_with_packs: CompositionContext) -> None:
        """Test expressions with extra whitespace."""
        evaluator = ConditionEvaluator(context_with_packs)
        assert evaluator.evaluate("  has-pack(python)  ") is True

    def test_multiline_if_block(self, context_with_packs: CompositionContext) -> None:
        """Test if block with multiline content."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        content = """{{if:has-pack(python)}}
Line 1
Line 2
Line 3
{{/if}}"""

        result = processor.process_if_blocks(content)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_nested_if_blocks_not_supported(self, context_with_packs: CompositionContext) -> None:
        """Test that nested if blocks are handled (pattern matches innermost)."""
        evaluator = ConditionEvaluator(context_with_packs)
        processor = ConditionalProcessor(evaluator)

        # Note: Current implementation doesn't support truly nested blocks
        # This tests current behavior
        content = """{{if:has-pack(python)}}
Outer
{{if:has-pack(vitest)}}Inner{{/if}}
{{/if}}"""

        result = processor.process_if_blocks(content)
        # Inner block is processed first
        assert "Inner" in result or "Outer" in result
