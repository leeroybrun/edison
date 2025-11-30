import pytest
import yaml
from pathlib import Path
from edison.core.config.domains import workflow
from edison.core.config.domains.workflow import (
    WorkflowConfig,
    load_workflow_config,
    get_task_states,
    get_qa_states,
    get_semantic_state
)

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


def test_workflow_yaml_structure():
    """Workflow.yaml must be nested under 'workflow:' key and not duplicate states."""
    workflow_yaml = yaml.safe_load(Path("src/edison/data/config/workflow.yaml").read_text()) or {}

    # Content should be under 'workflow' key (consistent with other domain configs)
    assert "workflow" in workflow_yaml, "workflow.yaml should have content under 'workflow:' key"
    wf_section = workflow_yaml["workflow"]

    # Must not duplicate state definitions (sourced from state-machine.yaml)
    assert "taskStates" not in wf_section, "workflow.yaml should not duplicate taskStates"
    assert "qaStates" not in wf_section, "workflow.yaml should not duplicate qaStates"


def test_workflow_states_source_state_machine():
    """States should be sourced from state-machine.yaml, not workflow.yaml."""
    state_machine_yaml = yaml.safe_load(Path("src/edison/data/config/state-machine.yaml").read_text()) or {}
    sm_root = state_machine_yaml.get("statemachine") or {}
    task_states = list((sm_root.get("task") or {}).get("states", {}).keys())
    qa_states = list((sm_root.get("qa") or {}).get("states", {}).keys())

    assert task_states, "state-machine.yaml must declare task states"
    assert qa_states, "state-machine.yaml must declare QA states"

    # get_task_states/get_qa_states should be driven by the canonical state-machine file
    assert get_task_states(force_reload=True) == task_states
    assert get_qa_states(force_reload=True) == qa_states
