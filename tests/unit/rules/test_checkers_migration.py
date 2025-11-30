import pytest
import json
from pathlib import Path
from edison.core.rules.checkers import _load_json_safe, check_validator_approval
from edison.core.rules.models import Rule

def test_load_json_safe_migration(tmp_path):
    """Test _load_json_safe behavior."""
    path = tmp_path / "test.json"
    
    # Case 1: Valid JSON
    path.write_text('{"key": "value"}')
    assert _load_json_safe(path) == {"key": "value"}
    
    # Case 2: Invalid JSON
    path.write_text('{invalid')
    assert _load_json_safe(path) == {}
    
    # Case 3: Missing file
    non_existent = tmp_path / "missing.json"
    assert _load_json_safe(non_existent) == {}

def test_check_validator_approval_reads_bundle(tmp_path, monkeypatch):
    """Test that check_validator_approval correctly reads the bundle file."""
    
    # Setup
    bundle_path = tmp_path / "bundle-approved.json"
    bundle_data = {"approved": True}
    bundle_path.write_text(json.dumps(bundle_data))
    
    task = {"validation": {"reportPath": str(bundle_path)}}
    rule = Rule(id="r1", description="Test rule", blocking=True)
    
    # Mock PathResolver/Path handling if needed, but here we pass explicit path
    # so it should use it directly.
    
    # Act
    result = check_validator_approval(task, rule)
    
    # Assert
    assert result is True
