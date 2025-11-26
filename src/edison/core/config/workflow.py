from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from edison.data import read_yaml as real_read_yaml, file_exists as real_file_exists

_WORKFLOW_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def load_workflow_config(
    force_reload: bool = False,
    read_yaml_func: Callable[[str, str], Dict[str, Any]] = real_read_yaml,
    file_exists_func: Callable[[str, str], bool] = real_file_exists,
) -> Dict[str, Any]:
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
        
    if not file_exists_func("config", "workflow.yaml"):
        raise FileNotFoundError("workflow.yaml not found in edison.data.config")

    task_states, qa_states = _load_state_machine_states(
        read_yaml_func=read_yaml_func, file_exists_func=file_exists_func
    )

    try:
        raw_config = read_yaml_func("config", "workflow.yaml")
    except Exception as e:
        raise ValueError(f"Failed to parse workflow.yaml: {e}")

    _validate_workflow_config(raw_config)

    config: Dict[str, Any] = {
        "version": raw_config.get("version"),
        "validationLifecycle": raw_config["validationLifecycle"],
        "timeouts": raw_config["timeouts"],
        "taskStates": task_states,
        "qaStates": qa_states,
    }

    if not force_reload and read_yaml_func == real_read_yaml:
        # Only cache if using default readers (production mode)
        _WORKFLOW_CONFIG_CACHE = config

    return config


def _validate_workflow_config(config: Dict[str, Any]) -> None:
    """Validate the structure of the workflow configuration.

    State lists must come from state-machine.yaml to avoid duplication.
    """
    if not config:
        raise ValueError("workflow.yaml is empty")

    forbidden_keys = [k for k in ("qaStates", "taskStates") if k in config]
    if forbidden_keys:
        raise ValueError(
            "workflow.yaml must not define state lists (qaStates/taskStates); "
            "they are sourced from state-machine.yaml"
        )

    required_keys = ["validationLifecycle", "timeouts"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"workflow.yaml missing required key: {key}")

    if not isinstance(config["validationLifecycle"], dict):
        raise ValueError("validationLifecycle must be a dict")

    if not isinstance(config["timeouts"], dict):
        raise ValueError("timeouts must be a dict")


def _load_state_machine_states(
    read_yaml_func: Callable[[str, str], Dict[str, Any]] = real_read_yaml,
    file_exists_func: Callable[[str, str], bool] = real_file_exists,
) -> Tuple[List[str], List[str]]:
    """Load task and QA states from the canonical state-machine config."""
    if not file_exists_func("config", "state-machine.yaml"):
        raise FileNotFoundError("state-machine.yaml not found in edison.data.config")

    try:
        sm = read_yaml_func("config", "state-machine.yaml") or {}
    except Exception as exc:
        raise ValueError(f"Failed to parse state-machine.yaml: {exc}")

    statemachine = sm.get("statemachine")
    if not isinstance(statemachine, dict):
        raise ValueError("state-machine.yaml missing 'statemachine' root object")

    def _states(domain: str) -> List[str]:
        domain_cfg = statemachine.get(domain)
        if not isinstance(domain_cfg, dict):
            raise ValueError(f"state-machine.yaml missing statemachine.{domain} definition")
        states_cfg = domain_cfg.get("states")
        if isinstance(states_cfg, dict):
            return list(states_cfg.keys())
        if isinstance(states_cfg, list):
            return [str(s) for s in states_cfg]
        raise ValueError(f"statemachine.{domain}.states must be a dict or list")

    task_states = _states("task")
    qa_states = _states("qa")

    if not task_states or not qa_states:
        raise ValueError("state-machine.yaml must declare task and QA states")

    return task_states, qa_states


def get_task_states(**kwargs) -> List[str]:
    """Get allowed task states."""
    config = load_workflow_config(**kwargs)
    return config["taskStates"]


def get_qa_states(**kwargs) -> List[str]:
    """Get allowed QA states."""
    config = load_workflow_config(**kwargs)
    return config["qaStates"]


def get_lifecycle_transition(event: str, **kwargs) -> Dict[str, str]:
    """Get transition details for a lifecycle event (onApprove, onReject, onRevalidate)."""
    config = load_workflow_config(**kwargs)
    return config["validationLifecycle"].get(event, {})


def get_timeout(name: str, **kwargs) -> str:
    """Get a timeout value by name."""
    config = load_workflow_config(**kwargs)
    return config["timeouts"].get(name, "")

def _parse_transition_target(transition: str) -> str:
    if not transition or "→" not in transition:
        return ""
    return transition.split("→")[1].strip()

def _parse_transition_source(transition: str) -> str:
    if not transition or "→" not in transition:
        return ""
    return transition.split("→")[0].strip()

def get_semantic_state(domain: str, semantic_key: str, **kwargs) -> str:
    """
    Resolve a semantic state (e.g. 'wip', 'todo') to the configured state name.
    Uses validationLifecycle to infer states where possible.
    """
    config = load_workflow_config(**kwargs)
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
