import pytest
from pathlib import Path
import yaml
from unittest.mock import patch, MagicMock
from edison.core.config import (
    workflow, 
    load_workflow_config, 
    get_task_states, 
    get_qa_states,
    get_semantic_state
)

def test_workflow_module_exists():
    """Test that the workflow module exists."""
    assert workflow is not None, "edison.core.config.workflow module should exist"

def test_load_workflow_config_exists():
    """Test that load_workflow_config function exists."""
    assert callable(load_workflow_config), "load_workflow_config function should exist"

def test_workflow_config_structure():
    """Test that the loaded configuration has the correct structure."""
    config = load_workflow_config()
    assert "qaStates" in config
    assert "taskStates" in config
    assert "validationLifecycle" in config
    assert "timeouts" in config
    
    assert isinstance(config["qaStates"], list)
    assert "todo" in config["qaStates"]
    
    assert isinstance(config["taskStates"], list)
    assert "todo" in config["taskStates"]

def test_get_states_helpers():
    """Test helper functions for states."""
    task_states = get_task_states()
    qa_states = get_qa_states()
    
    assert isinstance(task_states, list)
    assert "todo" in task_states
    assert "done" in task_states
    
    assert isinstance(qa_states, list)
    assert "waiting" in qa_states
    assert "validated" in qa_states

def test_get_semantic_state():
    """Test retrieving semantic states from lifecycle."""
    # task done -> wip (onReject)
    assert get_semantic_state("task", "wip") == "wip"
    
    # task done -> validated (onApprove)
    assert get_semantic_state("task", "validated") == "validated"
    
    # qa wip -> waiting (onReject)
    assert get_semantic_state("qa", "wip") == "wip"
    assert get_semantic_state("qa", "waiting") == "waiting"
    
    # qa waiting -> todo (onRevalidate)
    assert get_semantic_state("qa", "todo") == "todo"

def test_default_workflow_yaml_exists():
    """Test that the actual workflow.yaml file exists in the codebase."""
    real_yaml_path = Path("src/edison/data/config/workflow.yaml")
    assert real_yaml_path.exists(), "src/edison/data/config/workflow.yaml should exist"

def test_invalid_config_raises_error():
    """Test that invalid config raises ValueError."""
    with patch("edison.core.config.workflow.read_yaml") as mock_read:
        # Missing required keys
        mock_read.return_value = {"version": "1.0.0"}
        # We need to force reload or patch the cache
        with patch("edison.core.config.workflow._WORKFLOW_CONFIG_CACHE", None):
            with pytest.raises(ValueError, match="missing required key"):
                load_workflow_config(force_reload=True)

def test_missing_file_raises_error():
    """Test that missing file raises FileNotFoundError."""
    with patch("edison.core.config.workflow.file_exists") as mock_exists:
        mock_exists.return_value = False
        with patch("edison.core.config.workflow._WORKFLOW_CONFIG_CACHE", None):
            with pytest.raises(FileNotFoundError, match="workflow.yaml not found"):
                load_workflow_config(force_reload=True)