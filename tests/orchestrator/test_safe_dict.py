"""Tests for SafeDict utility."""

import pytest


def test_safe_dict_preserves_unknown_placeholders():
    """SafeDict should preserve unknown placeholders instead of raising KeyError."""
    from edison.core.orchestrator.utils import SafeDict

    tokens = SafeDict({"name": "Alice", "age": "30"})

    # Test with known placeholders - should substitute
    result = "Hello {name}, you are {age} years old".format_map(tokens)
    assert result == "Hello Alice, you are 30 years old"

    # Test with unknown placeholders - should preserve
    result = "Hello {name}, ID: {id}".format_map(tokens)
    assert result == "Hello Alice, ID: {id}"

    # Test with only unknown placeholders - should preserve all
    result = "System: {system}, User: {user}".format_map(tokens)
    assert result == "System: {system}, User: {user}"

    # Test with mixed known and unknown
    result = "{name} works at {company} in {city}".format_map(tokens)
    assert result == "Alice works at {company} in {city}"


def test_safe_dict_works_like_normal_dict():
    """SafeDict should behave like a normal dict for direct access."""
    from edison.core.orchestrator.utils import SafeDict

    tokens = SafeDict({"key1": "value1", "key2": "value2"})

    # Test direct access
    assert tokens["key1"] == "value1"
    assert tokens["key2"] == "value2"

    # Test get method
    assert tokens.get("key1") == "value1"
    assert tokens.get("nonexistent", "default") == "default"

    # Test keys, values, items
    assert set(tokens.keys()) == {"key1", "key2"}
    assert set(tokens.values()) == {"value1", "value2"}

    # Test iteration
    keys = [k for k in tokens]
    assert set(keys) == {"key1", "key2"}


def test_safe_dict_empty():
    """SafeDict should work with empty dict."""
    from edison.core.orchestrator.utils import SafeDict

    tokens = SafeDict()

    # All placeholders should be preserved when dict is empty
    result = "Hello {name}, ID: {id}".format_map(tokens)
    assert result == "Hello {name}, ID: {id}"


def test_safe_dict_nested_braces():
    """SafeDict should preserve nested or escaped braces."""
    from edison.core.orchestrator.utils import SafeDict

    tokens = SafeDict({"var": "value"})

    # Simple placeholder
    result = "{var}".format_map(tokens)
    assert result == "value"

    # Unknown placeholder
    result = "{unknown}".format_map(tokens)
    assert result == "{unknown}"

    # Mixed
    result = "{var} {unknown}".format_map(tokens)
    assert result == "value {unknown}"
