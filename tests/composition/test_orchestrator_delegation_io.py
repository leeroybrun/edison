import json
from pathlib import Path
from unittest.mock import patch
from edison.core.composition.orchestrator import load_delegation_config
from edison.core.file_io import utils as io_utils

def test_load_delegation_config_uses_safe_io(tmp_path):
    """Verify load_delegation_config uses read_json_safe for robust loading."""
    core_dir = tmp_path / "core"
    project_dir = tmp_path / "project"
    
    # Setup directories
    (core_dir / "delegation").mkdir(parents=True)
    (project_dir / "delegation").mkdir(parents=True)
    
    # Create a config file
    expected_data = {"roleMapping": {"expert": "senior"}}
    config_path = project_dir / "delegation" / "config.json"
    config_path.write_text(json.dumps(expected_data), encoding="utf-8")
    
    # Patch read_json_safe in the orchestrator module where it is used
    with patch("edison.core.composition.orchestrator.read_json_safe", wraps=io_utils.read_json_safe) as mock_read:
        result = load_delegation_config({}, core_dir, project_dir)
        
        # Verify functionality
        assert result["roleMapping"] == {"expert": "senior"}
        
        # Verify implementation (Should fail before refactor)
        # We expect at least one call corresponding to the file we created
        # Note: The loop checks core_dir and project_dir. 
        # If project_dir exists, it should be read.
        
        # We filter calls to ensuring it was called with our path
        # (This avoids counting calls from other parts if any, though unlikely in this unit)
        called_paths = [c.args[0] for c in mock_read.call_args_list]
        assert config_path in called_paths, f"Expected read_json_safe to be called with {config_path}"
