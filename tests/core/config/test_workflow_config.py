import pytest
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from edison.core.config import (
    workflow, 
    load_workflow_config, 
    get_task_states, 
    get_qa_states,
    get_semantic_state
)

# --- Test Helpers ---

def make_fake_read_yaml(
    return_value: Optional[Dict[str, Any]] = None,
    side_effect: Optional[Exception] = None,
):
    """Return a fake reader that still loads the real state-machine config."""

    def fake_read(domain: str, filename: str) -> Dict[str, Any]:
        if filename == "state-machine.yaml":
            from edison.data import read_yaml

            return read_yaml(domain, filename)
        if side_effect:
            raise side_effect
        if return_value is not None:
            return return_value
        return {}

    return fake_read

def make_fake_file_exists(return_value: bool):
    def fake_exists(domain: str, filename: str) -> bool:
        return return_value
    return fake_exists

# --- Tests ---

def test_workflow_module_exists():
    """Test that the workflow module exists."""
    assert workflow is not None, "edison.core.config.workflow module should exist"

def test_load_workflow_config_exists():
    """Test that load_workflow_config function exists."""
    assert callable(load_workflow_config), "load_workflow_config function should exist"

def test_workflow_config_structure():
    """Test that the loaded configuration has the correct structure."""
    # Using real implementation here as integration test
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
    """Test that invalid config raises ValueError using dependency injection."""
    # Missing required keys
    fake_read = make_fake_read_yaml(return_value={"version": "1.0.0"})
    fake_exists = make_fake_file_exists(True)
    
    with pytest.raises(ValueError, match="missing required key"):
        load_workflow_config(
            force_reload=True,
            read_yaml_func=fake_read,
            file_exists_func=fake_exists
        )

def test_malformed_yaml_raises_error():
    """Test that malformed yaml raises ValueError using dependency injection."""
    fake_read = make_fake_read_yaml(side_effect=Exception("Bad YAML"))
    fake_exists = make_fake_file_exists(True)

    with pytest.raises(ValueError, match="Failed to parse workflow.yaml"):
        load_workflow_config(
            force_reload=True,
            read_yaml_func=fake_read,
            file_exists_func=fake_exists
        )

def test_missing_file_raises_error():
    """Test that missing file raises FileNotFoundError using dependency injection."""
    fake_exists = make_fake_file_exists(False)
    
    with pytest.raises(FileNotFoundError, match="workflow.yaml not found"):
        load_workflow_config(
            force_reload=True,
            file_exists_func=fake_exists
        )


def test_workflow_states_source_state_machine():
    """Workflow config must not duplicate state definitions."""
    workflow_yaml = yaml.safe_load(Path("src/edison/data/config/workflow.yaml").read_text()) or {}
    assert "taskStates" not in workflow_yaml, "workflow.yaml should not duplicate taskStates; source them from state-machine.yaml"
    assert "qaStates" not in workflow_yaml, "workflow.yaml should not duplicate qaStates; source them from state-machine.yaml"

    state_machine_yaml = yaml.safe_load(Path("src/edison/data/config/state-machine.yaml").read_text()) or {}
    sm_root = state_machine_yaml.get("statemachine") or {}
    task_states = list((sm_root.get("task") or {}).get("states", {}).keys())
    qa_states = list((sm_root.get("qa") or {}).get("states", {}).keys())

    assert task_states, "state-machine.yaml must declare task states"
    assert qa_states, "state-machine.yaml must declare QA states"

    # get_task_states/get_qa_states should be driven by the canonical state-machine file
    assert get_task_states(force_reload=True) == task_states
    assert get_qa_states(force_reload=True) == qa_states
