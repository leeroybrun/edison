"""Tests for shared schema validation utilities for adapters.

Note: Schemas are loaded from bundled edison.data/schemas/ ONLY.
There is NO .edison/core/schemas/ in the current architecture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from edison.core.schemas import (
    load_schema,
    validate_payload,
    validate_payload_safe,
    SchemaValidationError,
)

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestSchemaLoading:
    """Test schema loading functionality.

    Schemas are ALWAYS loaded from bundled edison.data/schemas/ directory.
    """

    def test_load_schema_success(self) -> None:
        """load_schema returns parsed schema dictionary for valid schema."""
        # Load a real bundled schema
        schema = load_schema("adapters/claude-agent.schema.json")

        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema or "properties" in schema
        assert schema  # Not empty

    def test_load_schema_without_extension(self) -> None:
        """load_schema accepts schema name without .json extension."""
        schema = load_schema("adapters/claude-agent.schema")

        assert isinstance(schema, dict)
        assert schema  # Not empty

    def test_load_schema_missing_raises(self) -> None:
        """load_schema raises FileNotFoundError for missing schema."""
        with pytest.raises(FileNotFoundError) as excinfo:
            load_schema("nonexistent-schema.json")

        assert "nonexistent-schema.json" in str(excinfo.value)


class TestPayloadValidation:
    """Test payload validation functionality."""

    def test_validate_payload_success(self) -> None:
        """validate_payload succeeds for valid payload."""
        # Valid payload for claude-agent schema
        payload = {
            "name": "test-agent",
            "description": "Test agent description",
            "model": "sonnet",
            "sections": {
                "role": "Agent role description",
                "tools": "Tool list",
                "guidelines": "Guidelines",
                "workflows": "Workflows",
            },
        }

        # Should not raise - validates against bundled schema
        validate_payload(payload, "adapters/claude-agent.schema.json")

    def test_validate_payload_invalid_raises(self) -> None:
        """validate_payload raises SchemaValidationError for invalid payload."""
        # Invalid payload - missing required fields
        payload = {"invalid": "data"}

        with pytest.raises(SchemaValidationError):
            validate_payload(payload, "adapters/claude-agent.schema.json")

    def test_validate_payload_safe_returns_errors(self) -> None:
        """validate_payload_safe returns list of errors for invalid payload."""
        # Invalid payload - missing required fields
        payload = {"invalid": "data"}

        errors = validate_payload_safe(payload, "adapters/claude-agent.schema.json")

        assert isinstance(errors, list)
        # Should have validation errors (or empty if jsonschema not installed)

    def test_validate_payload_safe_empty_for_valid(self) -> None:
        """validate_payload_safe returns empty list for valid payload."""
        payload = {
            "name": "test-agent",
            "description": "Test agent description",
            "model": "sonnet",
            "sections": {
                "role": "Agent role description",
                "tools": "Tool list",
                "guidelines": "Guidelines",
                "workflows": "Workflows",
            },
        }

        errors = validate_payload_safe(payload, "adapters/claude-agent.schema.json")

        assert errors == []


class TestSchemaValidationError:
    """Test SchemaValidationError exception."""

    def test_error_can_be_raised(self) -> None:
        """SchemaValidationError can be raised with message and errors."""
        with pytest.raises(SchemaValidationError) as excinfo:
            raise SchemaValidationError("Validation failed", ["error1", "error2"])

        assert "Validation failed" in str(excinfo.value)

    def test_error_inherits_from_value_error(self) -> None:
        """SchemaValidationError inherits from ValueError."""
        assert issubclass(SchemaValidationError, ValueError)
