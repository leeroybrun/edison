from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from edison.data import read_yaml, file_exists

_WORKFLOW_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def load_workflow_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load the workflow configuration from workflow.yaml.
    
    Returns:
        Dict containing the workflow configuration.
        
    Raises:
        FileNotFoundError: If workflow.yaml is not found.
        ValueError: If workflow.yaml is invalid.
    """
    global _WORKFLOW_CONFIG_CACHE
    
    if _WORKFLOW_CONFIG_CACHE is not None and not force_reload:
        return _WORKFLOW_CONFIG_CACHE
        
    if not file_exists("config", "workflow.yaml"):
        raise FileNotFoundError("workflow.yaml not found in edison.data.config")
        
    try:
        config = read_yaml("config", "workflow.yaml")
    except Exception as e:
        raise ValueError(f"Failed to parse workflow.yaml: {e}")
        
    _validate_workflow_config(config)
    
    _WORKFLOW_CONFIG_CACHE = config
    return config


def _validate_workflow_config(config: Dict[str, Any]) -> None:
    """Validate the structure of the workflow configuration."""
    if not config:
        raise ValueError("workflow.yaml is empty")
        
    required_keys = ["qaStates", "taskStates", "validationLifecycle", "timeouts"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"workflow.yaml missing required key: {key}")
            
    if not isinstance(config["qaStates"], list):
        raise ValueError("qaStates must be a list")
        
    if not isinstance(config["taskStates"], list):
        raise ValueError("taskStates must be a list")
        
    if not isinstance(config["validationLifecycle"], dict):
        raise ValueError("validationLifecycle must be a dict")
        
    if not isinstance(config["timeouts"], dict):
        raise ValueError("timeouts must be a dict")


def get_task_states() -> List[str]:
    """Get allowed task states."""
    config = load_workflow_config()
    return config["taskStates"]


def get_qa_states() -> List[str]:
    """Get allowed QA states."""
    config = load_workflow_config()
    return config["qaStates"]


def get_lifecycle_transition(event: str) -> Dict[str, str]:
    """Get transition details for a lifecycle event (onApprove, onReject, onRevalidate)."""
    config = load_workflow_config()
    return config["validationLifecycle"].get(event, {})


def get_timeout(name: str) -> str:
    """Get a timeout value by name."""
    config = load_workflow_config()
    return config["timeouts"].get(name, "")

def _parse_transition_target(transition: str) -> str:
    if not transition or "→" not in transition:
        return ""
    return transition.split("→")[1].strip()

def _parse_transition_source(transition: str) -> str:
    if not transition or "→" not in transition:
        return ""
    return transition.split("→")[0].strip()

def get_semantic_state(domain: str, semantic_key: str) -> str:
    """
    Resolve a semantic state (e.g. 'wip', 'todo') to the configured state name.
    Uses validationLifecycle to infer states where possible.
    """
    config = load_workflow_config()
    lc = config.get("validationLifecycle", {})
    
    # Common derivations
    on_approve = lc.get("onApprove", {})
    on_reject = lc.get("onReject", {})
    on_revalidate = lc.get("onRevalidate", {})
    
    if domain == "task":
        # validated: target of onApprove
        if semantic_key == "validated":
            return _parse_transition_target(on_approve.get("taskState", "")) or "validated"
        # done: source of onApprove
        if semantic_key == "done":
            return _parse_transition_source(on_approve.get("taskState", "")) or "done"
        # wip: target of onReject (done -> wip)
        if semantic_key == "wip":
            return _parse_transition_target(on_reject.get("taskState", "")) or "wip"
        # todo: default, not in lifecycle for task typically. Assume "todo" or first state?
        if semantic_key == "todo":
            # Check if "todo" is in taskStates
            states = config.get("taskStates", [])
            if "todo" in states: return "todo"
            return states[0] if states else "todo"

    if domain == "qa":
        # validated: target of onApprove
        if semantic_key == "validated":
            return _parse_transition_target(on_approve.get("qaState", "")) or "validated"
        # done: source of onApprove
        if semantic_key == "done":
            return _parse_transition_source(on_approve.get("qaState", "")) or "done"
        # wip: source of onReject (wip -> waiting)
        if semantic_key == "wip":
            return _parse_transition_source(on_reject.get("qaState", "")) or "wip"
        # waiting: target of onReject
        if semantic_key == "waiting":
            return _parse_transition_target(on_reject.get("qaState", "")) or "waiting"
        # todo: target of onRevalidate (waiting -> todo)
        if semantic_key == "todo":
            return _parse_transition_target(on_revalidate.get("qaState", "")) or "todo"
            
    return semantic_key