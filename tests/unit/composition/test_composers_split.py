#!/usr/bin/env python3
"""Tests for composers.py split structure.

This test validates that composers.py has been properly split into a package
following the 200 LOC per file limit while maintaining backward compatibility.
"""
from __future__ import annotations

import pytest
from pathlib import Path


def test_composers_is_package() -> None:
    """Composers should be a package (directory) not a single file."""
    from edison.core.composition import composers

    composers_path = Path(composers.__file__).parent
    assert composers_path.name == "composers", \
        "composers should be a package directory"
    assert (composers_path / "__init__.py").exists(), \
        "composers package must have __init__.py"


def test_split_modules_exist() -> None:
    """All expected split modules should exist."""
    from edison.core.composition import composers

    composers_dir = Path(composers.__file__).parent
    expected_modules = [
        "base.py",
        "prompt.py",
        "zen.py",
        "guideline.py",
        "engine.py",
    ]

    for module_name in expected_modules:
        module_path = composers_dir / module_name
        assert module_path.exists(), \
            f"Module {module_name} should exist in composers package"


def test_split_modules_under_loc_limit() -> None:
    """Each split module should be under LOC limits (200 for most, 350 for engine)."""
    from edison.core.composition import composers

    composers_dir = Path(composers.__file__).parent
    # engine.py gets higher limit as it's the main orchestration class
    modules_to_check = {
        "base.py": 200,
        "prompt.py": 200,
        "zen.py": 200,
        "guideline.py": 200,
        "engine.py": 350,  # Higher limit for core orchestration class
    }

    for module_name, limit in modules_to_check.items():
        module_path = composers_dir / module_name
        if module_path.exists():
            lines = module_path.read_text(encoding="utf-8").splitlines()
            loc = len(lines)
            assert loc < limit, \
                f"{module_name} has {loc} lines (limit: {limit})"


def test_public_api_imports_work() -> None:
    """All public API symbols from __all__ should be importable."""
    expected_symbols = [
        "ComposeError",
        "ComposeResult",
        "compose_prompt",
        "compose_guidelines",
        "compose_zen_prompt",
        "compose_agent_zen_prompt",
        "compose_validator_zen_prompt",
        "resolve_includes",
        "render_conditional_includes",
        "auto_activate_packs",
        "validate_composition",
        "dry_duplicate_report",
        "ENGINE_VERSION",
        "MAX_DEPTH",
        "CompositionEngine",
        "get_cache_dir",
        "_strip_headings_and_code",
        "_tokenize",
        "_shingles",
        "_repo_root",
    ]

    from edison.core.composition import composers

    for symbol in expected_symbols:
        assert hasattr(composers, symbol), \
            f"Symbol '{symbol}' should be exported from composers"


def test_compose_result_dataclass_exists() -> None:
    """ComposeResult dataclass should be importable."""
    from edison.core.composition.composers import ComposeResult

    # Should be a dataclass
    assert hasattr(ComposeResult, "__dataclass_fields__"), \
        "ComposeResult should be a dataclass"

    # Should have expected fields
    fields = ComposeResult.__dataclass_fields__
    expected_fields = {"text", "dependencies", "cache_path", "hash", "duplicate_report"}
    assert set(fields.keys()) == expected_fields, \
        f"ComposeResult should have fields {expected_fields}"


def test_compose_prompt_function_exists() -> None:
    """compose_prompt function should be importable and callable."""
    from edison.core.composition.composers import compose_prompt

    assert callable(compose_prompt), \
        "compose_prompt should be a callable function"


def test_composition_engine_class_exists() -> None:
    """CompositionEngine class should be importable."""
    from edison.core.composition.composers import CompositionEngine

    # Should be a class
    assert isinstance(CompositionEngine, type), \
        "CompositionEngine should be a class"

    # Should have expected methods
    expected_methods = [
        "__init__",
        "compose_validators",
        "compose_guidelines",
        "compose_zen_prompts",
        "compose_commands",
    ]

    for method_name in expected_methods:
        assert hasattr(CompositionEngine, method_name), \
            f"CompositionEngine should have method '{method_name}'"


def test_zen_composers_exist() -> None:
    """Zen composition functions should be importable."""
    from edison.core.composition.composers import (
        compose_zen_prompt,
        compose_agent_zen_prompt,
        compose_validator_zen_prompt,
    )

    assert callable(compose_zen_prompt), \
        "compose_zen_prompt should be callable"
    assert callable(compose_agent_zen_prompt), \
        "compose_agent_zen_prompt should be callable"
    assert callable(compose_validator_zen_prompt), \
        "compose_validator_zen_prompt should be callable"


def test_compose_guidelines_function_exists() -> None:
    """compose_guidelines standalone function should be importable."""
    from edison.core.composition.composers import compose_guidelines

    assert callable(compose_guidelines), \
        "compose_guidelines should be a callable function"


def test_backward_compatibility_imports() -> None:
    """Existing code importing from composers should still work."""
    # This tests the most common import pattern
    from edison.core.composition.composers import CompositionEngine, ComposeResult

    assert CompositionEngine is not None
    assert ComposeResult is not None


def test_no_circular_imports() -> None:
    """Importing composers should not cause circular import errors."""
    # This will fail if there are circular imports
    try:
        import edison.core.composition.composers
        from edison.core.composition.composers import CompositionEngine

        # Should be able to instantiate (may fail with config issues, but not import issues)
        # We're just testing imports here
        assert edison.core.composition.composers is not None
        assert CompositionEngine is not None
    except ImportError as e:
        pytest.fail(f"Circular import detected: {e}")


def test_original_composers_py_deleted() -> None:
    """The original composers.py file should be deleted after split."""
    from edison.core.composition import composers

    composers_dir = Path(composers.__file__).parent.parent
    original_file = composers_dir / "composers.py"

    # After the split, composers.py should NOT exist
    # (composers/__init__.py should exist instead)
    if original_file.exists():
        pytest.fail(
            "Original composers.py file still exists. "
            "It should be deleted after creating the composers/ package."
        )
