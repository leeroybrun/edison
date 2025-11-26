import os
from pathlib import Path
from unittest.mock import patch
import pytest
from edison.core.utils.paths.resolver import PathResolver
import edison.core.utils.io as io_utils

def test_detect_session_id_uses_read_json(tmp_path, monkeypatch):
    """
    Verify that detect_session_id uses read_json to read session.json.
    This ensures consistent file locking and error handling.
    """
    # Setup
    project_root = tmp_path
    # Create .project dir to mark it as root
    dot_project = project_root / ".project"
    dot_project.mkdir()
    
    # Create active session dir
    session_name = "test-session"
    session_dir = dot_project / "sessions" / "active" / session_name
    session_dir.mkdir(parents=True)
    
    # Create session.json
    session_json = session_dir / "session.json"
    # Using write_text to simulate existing file
    session_json.write_text('{"owner": "tester"}', encoding="utf-8")
    
    # Change cwd to project root
    monkeypatch.chdir(project_root)
    
    # Clear interfering env vars
    monkeypatch.delenv("project_SESSION", raising=False)
    monkeypatch.delenv("project_OWNER", raising=False)

    # Mock get_management_paths to ensure it finds our structure
    # But since we used standard structure, real one should work if resolve_project_root works.
    
    # Patch read_json to verify it is called
    # We patch where it is USED, not where it is defined
    with patch('edison.core.session.id.read_json', side_effect=io_utils.read_json) as mock_read:
        # Run
        # Explicitly set owner to match file
        result = PathResolver.detect_session_id(owner="tester")
        
        # Assert
        assert result == session_name, "Should detect session ID from owner"
        mock_read.assert_called()
