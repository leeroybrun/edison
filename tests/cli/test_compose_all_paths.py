import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from edison.cli.compose.all import main
from edison.core.paths.project import get_project_config_dir

@pytest.fixture
def mock_args():
    args = MagicMock()
    args.repo_root = None
    args.agents = False
    args.validators = False
    args.orchestrator = False
    args.guidelines = False
    args.dry_run = False
    args.json = False
    args.claude = False
    args.cursor = False
    args.zen = False
    args.platforms = None
    return args

def test_compose_all_uses_resolved_config_dir_for_validators(tmp_path, mock_args):
    """Test that validators are written to resolved config dir, not hardcoded .agents."""
    # Setup
    repo_root = tmp_path
    # Mock resolve_project_root to return our tmp_path
    with patch("edison.core.paths.resolve_project_root", return_value=repo_root), \
         patch("edison.core.composition.CompositionEngine") as MockEngine:
        
        # Configure mock engine
        engine = MockEngine.return_value
        # Return some dummy validator results
        val_result = MagicMock()
        val_result.text = "validator content"
        val_result.cache_path = Path("/tmp/cache/val.md")
        engine.compose_validators.return_value = {"test-val": val_result}
        
        # Enable only validators to focus test
        mock_args.validators = True
        
        # Execute
        main(mock_args)
        
        # Assert
        # We expect the code to use get_project_config_dir(repo_root) / "_generated" / "validators"
        # The current code uses repo_root / ".agents" / "_generated" / "validators"
        
        config_dir = get_project_config_dir(repo_root)
        expected_dir = config_dir / "_generated" / "validators"
        expected_file = expected_dir / "test-val.md"
        
        assert expected_file.exists(), f"Validator file should exist at {expected_file}"

def test_compose_all_uses_resolved_config_dir_for_orchestrator(tmp_path, mock_args):
    """Test that orchestrator manifest is written to resolved config dir."""
    # Setup
    repo_root = tmp_path
    with patch("edison.core.paths.resolve_project_root", return_value=repo_root), \
         patch("edison.core.composition.CompositionEngine") as MockEngine:
        
        engine = MockEngine.return_value
        engine.compose_orchestrator_manifest.return_value = {"manifest": Path("manifest.json")}
        
        # Enable only orchestrator
        mock_args.orchestrator = True
        
        # Execute
        main(mock_args)
        
        # Assert
        # The engine.compose_orchestrator_manifest is called with an output_dir
        # We verify it was called with the CORRECT directory
        
        config_dir = get_project_config_dir(repo_root)
        expected_output_dir = config_dir / "_generated"
        
        # Check calls
        engine.compose_orchestrator_manifest.assert_called_with(expected_output_dir)
