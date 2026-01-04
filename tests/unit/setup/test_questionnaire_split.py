"""Test that questionnaire module is properly split into separate concerns.

This test validates the split structure BEFORE implementation (TDD RED phase).
After the split is complete, these tests should pass (GREEN phase).
"""
from __future__ import annotations

import pytest


def test_questionnaire_base_module_exists():
    """Test that base module exists and contains SetupQuestionnaire class."""
    from edison.core.setup.questionnaire.base import SetupQuestionnaire

    assert SetupQuestionnaire is not None
    assert hasattr(SetupQuestionnaire, '__init__')
    assert hasattr(SetupQuestionnaire, 'run')


def test_questionnaire_prompts_module_exists():
    """Test that prompts module exists with prompting logic."""
    from edison.core.setup.questionnaire import prompts

    # Should contain prompt-related functions
    assert hasattr(prompts, 'prompt_user')
    assert hasattr(prompts, 'resolve_default_value')
    assert hasattr(prompts, 'resolve_options')


def test_questionnaire_validation_module_exists():
    """Test that validation module exists with validation logic."""
    from edison.core.setup.questionnaire import validation

    # Should contain validation and coercion functions
    assert hasattr(validation, 'coerce_value')
    assert hasattr(validation, 'validate_answer')


def test_questionnaire_rendering_module_exists():
    """Test that rendering module exists with template rendering."""
    from edison.core.setup.questionnaire import rendering

    # Should contain rendering functions
    assert hasattr(rendering, 'render_modular_configs')
    assert hasattr(rendering, 'render_readme_template')


def test_questionnaire_init_exports_main_class():
    """Test that __init__.py exports SetupQuestionnaire for backward compatibility."""
    from edison.core.setup.questionnaire import SetupQuestionnaire

    # Main class should be importable from package root
    assert SetupQuestionnaire is not None


def test_questionnaire_public_api_preserved():
    """Test that all public API methods are accessible from SetupQuestionnaire."""
    from edison.core.setup.questionnaire import SetupQuestionnaire

    # Public methods that existing code depends on
    public_methods = [
        'run',
        'defaults_for_mode',
        'render_modular_configs',
        'render_readme_template',
    ]

    for method_name in public_methods:
        assert hasattr(SetupQuestionnaire, method_name), f"Missing public method: {method_name}"


def test_split_modules_follow_single_responsibility():
    """Test that each module has a clear single responsibility."""
    from edison.core.setup.questionnaire import base, prompts, validation, rendering, context

    # Base: class definition and workflow
    assert hasattr(base, 'SetupQuestionnaire')

    # Prompts: user interaction and option resolution
    assert hasattr(prompts, 'prompt_user')
    assert hasattr(prompts, 'resolve_options')

    # Validation: type coercion and validation rules
    assert hasattr(validation, 'coerce_value')
    assert hasattr(validation, 'validate_answer')

    # Rendering: template processing and config generation
    assert hasattr(rendering, 'render_modular_configs')

    # Context: context and config building
    assert hasattr(context, 'build_context_with_defaults')
    assert hasattr(context, 'build_config_dict')


def test_backward_compatibility_with_existing_imports():
    """Test that existing import patterns still work."""
    # This is how existing tests import the class - now from core.setup
    from edison.core.setup.questionnaire import SetupQuestionnaire
    from edison.core.setup import SetupQuestionnaire as SetupQ2

    assert SetupQuestionnaire is SetupQ2

    # Should be able to instantiate
    assert SetupQuestionnaire is not None
