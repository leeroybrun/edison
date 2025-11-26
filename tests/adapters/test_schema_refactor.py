import json
import pytest
from unittest.mock import patch
from pathlib import Path
from edison.core.schemas import load_schema

@pytest.fixture
def schema_dir(tmp_path):
    """Create a temp schema directory with a test schema."""
    d = tmp_path / "schemas"
    d.mkdir()

    schema_content = {"type": "object", "properties": {"foo": {"type": "string"}}}
    (d / "test_schema.json").write_text(json.dumps(schema_content), encoding="utf-8")
    return d

def test_load_schema_uses_read_json_safe(schema_dir):
    """Verify load_schema handles files correctly with centralized I/O."""

    # Mock _get_schemas_dir to return our temp dir so we control the file system
    with patch("edison.core.schemas.validation._get_schemas_dir", return_value=schema_dir):
        result = load_schema("test_schema")

        # Verification of result (Real behavior)
        assert result == {"type": "object", "properties": {"foo": {"type": "string"}}}

def test_load_schema_handles_malformed_json(schema_dir):
    """Verify load_schema raises appropriate error for malformed JSON."""

    # Create a malformed JSON file
    (schema_dir / "bad_schema.json").write_text("{ invalid json }", encoding="utf-8")

    with patch("edison.core.schemas.validation._get_schemas_dir", return_value=schema_dir):
        with pytest.raises(json.JSONDecodeError):
            load_schema("bad_schema")
