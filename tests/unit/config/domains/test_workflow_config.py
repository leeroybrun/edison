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


def test_plan_states_from_config():
    """Plan states should be loaded from configuration by WorkflowConfig.

    Plans are Edison-managed artifacts with a lifecycle: draft -> approved -> archived.
    """
    config = WorkflowConfig()

    # Verify plan states are loaded via get_states
    plan_states = config.get_states("plan")
    assert plan_states, "WorkflowConfig must provide plan states"
    assert "draft" in plan_states, "Plan states must include 'draft'"
    assert "approved" in plan_states, "Plan states must include 'approved'"
    assert "archived" in plan_states, "Plan states must include 'archived'"


def test_plan_states_property():
    """WorkflowConfig should have a plan_states cached property."""
    config = WorkflowConfig()

    plan_states = config.plan_states
    assert isinstance(plan_states, list)
    assert "draft" in plan_states
    assert "approved" in plan_states
    assert "archived" in plan_states


def test_plan_initial_state():
    """Plan initial state should be 'draft'."""
    config = WorkflowConfig()

    initial = config.get_initial_state("plan")
    assert initial == "draft", "Plan initial state should be 'draft'"


def test_plan_final_state():
    """Plan final state should be 'archived'."""
    config = WorkflowConfig()

    final = config.get_final_state("plan")
    assert final == "archived", "Plan final state should be 'archived'"


def test_plan_transitions():
    """Plan should have valid state transitions."""
    config = WorkflowConfig()

    transitions = config.get_transitions("plan")
    assert transitions, "Plan should have transitions"

    # draft -> approved should be allowed
    assert "approved" in transitions.get("draft", []), "draft -> approved should be allowed"

    # approved -> archived should be allowed
    assert "archived" in transitions.get("approved", []), "approved -> archived should be allowed"

    # archived should have no transitions (final state)
    assert transitions.get("archived", []) == [], "archived should have no transitions"


def test_plan_is_terminal_state():
    """Archived should be a terminal state for plan."""
    config = WorkflowConfig()

    assert config.is_terminal_state("plan", "archived") is True
    assert config.is_terminal_state("plan", "draft") is False
    assert config.is_terminal_state("plan", "approved") is False
