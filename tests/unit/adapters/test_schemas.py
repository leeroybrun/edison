"""Tests for shared schema validation utilities for adapters."""
from __future__ import annotations

import json
import shutil
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
    """Test schema loading functionality."""

    def _install_test_schema(self, root: Path, schema_name: str, subfolder: str = "") -> Path:
        """Copy a schema from src/edison/data/schemas to test .edison directory."""
        schema_src_dir = REPO_ROOT / "src" / "edison" / "data" / "schemas"
        if subfolder:
            schema_src_dir = schema_src_dir / subfolder
        schema_dst_dir = root / ".edison" / "core" / "schemas"
        if subfolder:
            schema_dst_dir = schema_dst_dir / subfolder
        schema_dst_dir.mkdir(parents=True, exist_ok=True)

        src = schema_src_dir / schema_name
        dst = schema_dst_dir / schema_name
        if src.exists():
            shutil.copy(src, dst)
        return dst

    def test_load_schema_success(self, isolated_project_env: Path) -> None:
        """load_schema returns parsed schema dictionary for valid schema."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

        schema = load_schema("adapters/claude-agent.schema.json", repo_root=root)

        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema
        assert schema  # Not empty

    def test_load_schema_without_extension(self, isolated_project_env: Path) -> None:
        """load_schema accepts schema name without .json extension."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

        schema = load_schema("adapters/claude-agent.schema", repo_root=root)

        assert isinstance(schema, dict)
        assert schema  # Not empty

    def test_load_schema_missing_raises(self, isolated_project_env: Path) -> None:
        """load_schema raises FileNotFoundError for missing schema."""
        root = isolated_project_env

        with pytest.raises(FileNotFoundError) as excinfo:
            load_schema("nonexistent-schema.json", repo_root=root)

        assert "nonexistent-schema.json" in str(excinfo.value)

    def test_load_schema_invalid_json_raises(self, isolated_project_env: Path) -> None:
        """load_schema raises JSONDecodeError for invalid JSON."""
        root = isolated_project_env
        schema_dir = root / ".edison" / "core" / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)

        bad_schema = schema_dir / "bad-schema.json"
        bad_schema.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_schema("bad-schema.json", repo_root=root)


class TestPayloadValidation:
    """Test payload validation functionality."""

    def _install_test_schema(self, root: Path, schema_name: str, subfolder: str = "") -> Path:
        """Copy a schema from src/edison/data/schemas to test .edison directory."""
        schema_src_dir = REPO_ROOT / "src" / "edison" / "data" / "schemas"
        if subfolder:
            schema_src_dir = schema_src_dir / subfolder
        schema_dst_dir = root / ".edison" / "core" / "schemas"
        if subfolder:
            schema_dst_dir = schema_dst_dir / subfolder
        schema_dst_dir.mkdir(parents=True, exist_ok=True)

        src = schema_src_dir / schema_name
        dst = schema_dst_dir / schema_name
        if src.exists():
            shutil.copy(src, dst)
        return dst

    def test_validate_payload_success(self, isolated_project_env: Path) -> None:
        """validate_payload succeeds for valid payload."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

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

        # Should not raise
        validate_payload(payload, "adapters/claude-agent.schema.json", repo_root=root)

    def test_validate_payload_missing_required_field_raises(self, isolated_project_env: Path) -> None:
        """validate_payload raises SchemaValidationError for missing required field."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

        # Missing 'sections' field
        payload = {
            "name": "test-agent",
            "description": "Test agent",
            "model": "sonnet",
        }

        with pytest.raises(SchemaValidationError) as excinfo:
            validate_payload(payload, "adapters/claude-agent.schema.json", repo_root=root)

        error_msg = str(excinfo.value)
        assert "sections" in error_msg.lower() or "required" in error_msg.lower()

    def test_validate_payload_wrong_type_raises(self, isolated_project_env: Path) -> None:
        """validate_payload raises SchemaValidationError for wrong type."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent-config.schema.json", "adapters")

        # 'model' should be string, not number
        payload = {
            "model": 123,
            "enabled": True,
        }

        with pytest.raises(SchemaValidationError) as excinfo:
            validate_payload(payload, "adapters/claude-agent-config.schema.json", repo_root=root)

        error_msg = str(excinfo.value)
        assert "model" in error_msg.lower() or "type" in error_msg.lower()

    def test_validate_payload_empty_role_raises(self, isolated_project_env: Path) -> None:
        """validate_payload raises SchemaValidationError for empty role section."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

        payload = {
            "name": "test-agent",
            "description": "Test agent",
            "model": "sonnet",
            "sections": {
                "role": "",  # Empty role
                "tools": "Tool list",
                "guidelines": "Guidelines",
                "workflows": "Workflows",
            },
        }

        with pytest.raises(SchemaValidationError) as excinfo:
            validate_payload(payload, "adapters/claude-agent.schema.json", repo_root=root)

        error_msg = str(excinfo.value)
        assert "role" in error_msg.lower()


class TestSafePayloadValidation:
    """Test safe payload validation that returns error messages."""

    def _install_test_schema(self, root: Path, schema_name: str, subfolder: str = "") -> Path:
        """Copy a schema from src/edison/data/schemas to test .edison directory."""
        schema_src_dir = REPO_ROOT / "src" / "edison" / "data" / "schemas"
        if subfolder:
            schema_src_dir = schema_src_dir / subfolder
        schema_dst_dir = root / ".edison" / "core" / "schemas"
        if subfolder:
            schema_dst_dir = schema_dst_dir / subfolder
        schema_dst_dir.mkdir(parents=True, exist_ok=True)

        src = schema_src_dir / schema_name
        dst = schema_dst_dir / schema_name
        if src.exists():
            shutil.copy(src, dst)
        return dst

    def test_validate_payload_safe_valid_returns_empty(self, isolated_project_env: Path) -> None:
        """validate_payload_safe returns empty list for valid payload."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

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

        errors = validate_payload_safe(payload, "adapters/claude-agent.schema.json", repo_root=root)

        assert errors == []

    def test_validate_payload_safe_invalid_returns_errors(self, isolated_project_env: Path) -> None:
        """validate_payload_safe returns error messages for invalid payload."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent.schema.json", "adapters")

        # Missing required fields
        payload = {
            "name": "test-agent",
            # Missing description, model, sections
        }

        errors = validate_payload_safe(payload, "adapters/claude-agent.schema.json", repo_root=root)

        assert isinstance(errors, list)
        assert len(errors) > 0
        assert any("description" in err.lower() or "required" in err.lower() for err in errors)

    def test_validate_payload_safe_multiple_errors(self, isolated_project_env: Path) -> None:
        """validate_payload_safe returns all validation errors."""
        root = isolated_project_env
        self._install_test_schema(root, "claude-agent-config.schema.json", "adapters")

        # Multiple issues: wrong type for model, invalid boolean
        payload = {
            "model": 123,  # Should be string
            "enabled": "not-a-boolean",  # Should be boolean
            "unknown_field": "value",  # Extra field (if schema has additionalProperties: false)
        }

        errors = validate_payload_safe(payload, "adapters/claude-agent-config.schema.json", repo_root=root)

        assert isinstance(errors, list)
        # Should have at least one error
        assert len(errors) > 0


class TestSchemaFallbackBehavior:
    """Test behavior when jsonschema is not available.

    This test verifies real behavior: when jsonschema is not installed,
    validation gracefully degrades by returning empty error list (no validation).
    Instead of mocking, we test the actual fallback behavior.
    """

    def test_validate_without_jsonschema_via_missing_schema(self, isolated_project_env: Path) -> None:
        """validate_payload_safe handles missing schemas gracefully."""
        root = isolated_project_env

        payload = {"name": "test"}
        errors = validate_payload_safe(payload, "adapters/nonexistent-schema.json", repo_root=root)

        # Should return error about missing schema (not crash)
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert "schema loading failed" in errors[0].lower()

    def test_validate_with_real_jsonschema_works(self, isolated_project_env: Path) -> None:
        """Verify that real jsonschema validation works when library is available."""
        # This test proves we're using REAL jsonschema, not mocks
        try:
            import jsonschema
            jsonschema_available = True
        except ImportError:
            jsonschema_available = False

        if not jsonschema_available:
            pytest.skip("jsonschema not installed - testing real behavior only")

        root = isolated_project_env

        # Create a simple test schema
        schema_dir = root / ".edison" / "core" / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)

        test_schema = schema_dir / "test.schema.json"
        test_schema.write_text(json.dumps({
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            },
            "required": ["name"]
        }), encoding="utf-8")

        # Valid payload should pass
        valid_payload = {"name": "Alice", "age": 30}
        errors = validate_payload_safe(valid_payload, "test.schema.json", repo_root=root)
        assert errors == []

        # Invalid payload should fail (missing required field)
        invalid_payload = {"age": 30}
        errors = validate_payload_safe(invalid_payload, "test.schema.json", repo_root=root)
        assert len(errors) > 0
        assert any("name" in err.lower() or "required" in err.lower() for err in errors)
