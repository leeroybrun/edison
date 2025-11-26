
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from edison.core.orchestrator.launcher import OrchestratorLauncher, OrchestratorConfig, SessionContext

@pytest.fixture
def mock_context(tmp_path):
    ctx = MagicMock(spec=SessionContext)
    ctx.project_root = tmp_path
    ctx.session_id = "sess-123"
    ctx.session = {}
    return ctx

@pytest.fixture
def mock_config(tmp_path):
    cfg = MagicMock(spec=OrchestratorConfig)
    cfg.repo_root = tmp_path
    
    # Setup get_profile return value
    cfg.get_profile.return_value = {
        "command": "echo",
        "args": ["hello"],
        "cwd": "custom_cwd"
    }
    return cfg

def test_launcher_log_path_mkdir(tmp_path, mock_context, mock_config):
    launcher = OrchestratorLauncher(mock_config, mock_context)
    log_path = tmp_path / "logs" / "orch.log"
    
    # Ensure log dir doesn't exist
    assert not log_path.parent.exists()
    
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.poll.return_value = 0
        launcher.launch("default", log_path=log_path)
    
    assert log_path.parent.exists()
    assert log_path.exists()

def test_launcher_cwd_mkdir(tmp_path, mock_context, mock_config):
    launcher = OrchestratorLauncher(mock_config, mock_context)
    cwd_path = tmp_path / "custom_cwd"
    
    # Ensure cwd doesn't exist
    assert not cwd_path.exists()
    
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.poll.return_value = 0
        launcher.launch("default")
    
    assert cwd_path.exists()
    assert cwd_path.is_dir()
