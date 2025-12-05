import pytest
import yaml
from pathlib import Path
from edison.core.config.domains import workflow
from edison.core.config.domains.workflow import WorkflowConfig

# --- Tests ---

def test_workflow_module_exists():
    """Test that the workflow module exists."""
    assert workflow is not None, "edison.core.config.workflow module should exist"

def test_workflow_config_class_exists():
    """Test that WorkflowConfig class exists."""
    assert WorkflowConfig is not None, "WorkflowConfig class should exist"

def test_workflow_config_structure():
    """Test that the loaded configuration has the correct structure."""
    # Using real implementation here as integration test
    config = WorkflowConfig()
    qa_states = config.qa_states
    task_states = config.task_states
    validation_lifecycle = config.validation_lifecycle
    timeouts = config.timeouts
    
    assert isinstance(qa_states, list)
    assert "todo" in qa_states
    
    assert isinstance(task_states, list)
    assert "todo" in task_states

def test_get_states_methods():
    """Test WorkflowConfig state methods."""
    config = WorkflowConfig()
    task_states = config.task_states
    qa_states = config.qa_states
    
    assert isinstance(task_states, list)
    assert "todo" in task_states
    assert "done" in task_states
    
    assert isinstance(qa_states, list)
    assert "waiting" in qa_states
    assert "validated" in qa_states

def test_get_semantic_state():
    """Test retrieving semantic states from lifecycle."""
    config = WorkflowConfig()
    
    # task done -> wip (onReject)
    assert config.get_semantic_state("task", "wip") == "wip"
    
    # task done -> validated (onApprove)
    assert config.get_semantic_state("task", "validated") == "validated"
    
    # qa wip -> waiting (onReject)
    assert config.get_semantic_state("qa", "wip") == "wip"
    assert config.get_semantic_state("qa", "waiting") == "waiting"
    
    # qa waiting -> todo (onRevalidate)
    assert config.get_semantic_state("qa", "todo") == "todo"

def test_default_workflow_yaml_exists():
    """Test that the actual workflow.yaml file exists in the codebase."""
    from edison.data import get_data_path
    real_yaml_path = get_data_path("config", "workflow.yaml")
    assert real_yaml_path.exists(), "workflow.yaml should exist in edison.data.config"


def test_workflow_yaml_structure():
    """Workflow.yaml must be nested under 'workflow:' key and not duplicate states."""
    from edison.data import get_data_path
    workflow_path = get_data_path("config", "workflow.yaml")
    workflow_yaml = yaml.safe_load(workflow_path.read_text()) or {}

    # Content should be under 'workflow' key (consistent with other domain configs)
    assert "workflow" in workflow_yaml, "workflow.yaml should have content under 'workflow:' key"
    wf_section = workflow_yaml["workflow"]

    # Must not duplicate state definitions (sourced from state-machine.yaml)
    assert "taskStates" not in wf_section, "workflow.yaml should not duplicate taskStates"
    assert "qaStates" not in wf_section, "workflow.yaml should not duplicate qaStates"


def test_workflow_states_from_config():
    """States should be loaded from configuration by WorkflowConfig."""
    config = WorkflowConfig()
    
    # Verify task states are loaded
    task_states = config.task_states
    assert task_states, "WorkflowConfig must provide task states"
    assert "todo" in task_states, "Task states must include 'todo'"
    assert "wip" in task_states, "Task states must include 'wip'"
    assert "done" in task_states, "Task states must include 'done'"
    
    # Verify QA states are loaded
    qa_states = config.qa_states
    assert qa_states, "WorkflowConfig must provide QA states"
    assert "waiting" in qa_states, "QA states must include 'waiting'"
    assert "todo" in qa_states, "QA states must include 'todo'"
    assert "validated" in qa_states, "QA states must include 'validated'"
