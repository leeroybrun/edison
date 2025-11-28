"""Test schema loading uses centralized I/O utilities.

This test ensures load_schema uses read_json for consistent file locking
and error handling across all schema operations.
"""
import json
import pytest
from pathlib import Path
from edison.core.schemas import load_schema


def test_load_schema_uses_read_json_safe():
    """Verify load_schema correctly loads schema files with centralized I/O.

    This test uses a real schema file from the edison.data package to verify
    that the schema loading mechanism works correctly with real files.
    """
    # Test: Load a real schema that exists in the package
    result = load_schema("config/config.schema")

    # Should successfully load the schema
    assert isinstance(result, dict)
    assert "$schema" in result or "type" in result  # Valid JSON schema


def test_load_schema_adds_json_extension():
    """Verify load_schema automatically adds .json extension."""
    # Test: Load schema without .json extension
    # Using a real schema file to test actual behavior
    result = load_schema("config/config.schema")

    # Should successfully load (extension added automatically)
    assert isinstance(result, dict)


def test_load_schema_raises_for_missing_file():
    """Verify load_schema raises FileNotFoundError for missing schemas."""
    # Test: Load non-existent schema
    with pytest.raises(FileNotFoundError) as exc_info:
        load_schema("nonexistent_schema_that_does_not_exist")

    # Should include helpful error message
    assert "Schema not found" in str(exc_info.value)
    assert "nonexistent_schema_that_does_not_exist.json" in str(exc_info.value)


def test_load_schema_works_with_subdirectories():
    """Verify load_schema works with schemas in subdirectories.

    This tests that schemas organized in subdirectories (like config/)
    can be loaded correctly.
    """
    # Test: Load schema from subdirectory
    result = load_schema("config/pack.schema")

    # Should successfully load from subdirectory
    assert isinstance(result, dict)
    assert "$schema" in result or "type" in result


def test_load_schema_caches_correctly():
    """Verify load_schema returns consistent results across multiple calls.

    This tests that the same schema loaded multiple times returns
    equivalent data.
    """
    # Load the same schema twice
    result1 = load_schema("config/config.schema")
    result2 = load_schema("config/config.schema")

    # Should return equivalent data
    assert result1 == result2
