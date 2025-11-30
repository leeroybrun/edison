"""Domain-specific configuration for workflow lifecycle.

Provides cached access to workflow lifecycle configuration including
validation lifecycle transitions and timeouts.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base import BaseDomainConfig
from edison.data import read_yaml as real_read_yaml, file_exists as real_file_exists


class WorkflowConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for workflow lifecycle.

    Provides typed, cached access to workflow configuration including:
    - Validation lifecycle transitions
    - Workflow timeouts
    - Task and QA states (from state machine)

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "workflow"

    @cached_property
    def _workflow_yaml(self) -> Dict[str, Any]:
        """Load workflow.yaml from bundled data."""
        if not real_file_exists("config", "workflow.yaml"):
            raise FileNotFoundError("workflow.yaml not found in edison.data.config")

        try:
            raw_config = real_read_yaml("config", "workflow.yaml")
        except Exception as e:
            raise ValueError(f"Failed to parse workflow.yaml: {e}")

        self._validate_workflow_config(raw_config)
        return raw_config

    def _validate_workflow_config(self, config: Dict[str, Any]) -> None:
        """Validate the structure of the workflow configuration."""
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

    @cached_property
    def _state_machine_states(self) -> Tuple[List[str], List[str]]:
        """Load task and QA states from state machine config."""
        statemachine = self._config.get("statemachine", {})
        if not isinstance(statemachine, dict):
            # Try loading from bundled YAML
            if not real_file_exists("config", "state-machine.yaml"):
                raise FileNotFoundError("state-machine.yaml not found in edison.data.config")
            try:
                sm = real_read_yaml("config", "state-machine.yaml") or {}
            except Exception as exc:
                raise ValueError(f"Failed to parse state-machine.yaml: {exc}")
            statemachine = sm.get("statemachine", {})

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

    @cached_property
    def validation_lifecycle(self) -> Dict[str, Any]:
        """Get validation lifecycle configuration."""
        return self._workflow_yaml.get("validationLifecycle", {})

    @cached_property
    def timeouts(self) -> Dict[str, str]:
        """Get workflow timeout configuration."""
        return self._workflow_yaml.get("timeouts", {})

    @cached_property
    def task_states(self) -> List[str]:
        """Get allowed task states."""
        return self._state_machine_states[0]

    @cached_property
    def qa_states(self) -> List[str]:
        """Get allowed QA states."""
        return self._state_machine_states[1]

    def get_lifecycle_transition(self, event: str) -> Dict[str, str]:
        """Get transition details for a lifecycle event."""
        return self.validation_lifecycle.get(event, {})

    def get_timeout(self, name: str) -> str:
        """Get a timeout value by name."""
        return self.timeouts.get(name, "")

    def get_semantic_state(self, domain: str, semantic_key: str) -> str:
        """Resolve a semantic state to the configured state name."""
        lc = self.validation_lifecycle

        on_approve = lc.get("onApprove", {})
        on_reject = lc.get("onReject", {})
        on_revalidate = lc.get("onRevalidate", {})

        def _parse_target(transition: str) -> str:
            if not transition or "→" not in transition:
                return ""
            return transition.split("→")[1].strip()

        def _parse_source(transition: str) -> str:
            if not transition or "→" not in transition:
                return ""
            return transition.split("→")[0].strip()

        if domain == "task":
            if semantic_key == "validated":
                return _parse_target(on_approve.get("taskState", "")) or "validated"
            if semantic_key == "done":
                return _parse_source(on_approve.get("taskState", "")) or "done"
            if semantic_key == "wip":
                return _parse_target(on_reject.get("taskState", "")) or "wip"
            if semantic_key == "todo":
                states = self.task_states
                if "todo" in states:
                    return "todo"
                return states[0] if states else "todo"

        if domain == "qa":
            if semantic_key == "validated":
                return _parse_target(on_approve.get("qaState", "")) or "validated"
            if semantic_key == "done":
                return _parse_source(on_approve.get("qaState", "")) or "done"
            if semantic_key == "wip":
                return _parse_source(on_reject.get("qaState", "")) or "wip"
            if semantic_key == "waiting":
                return _parse_target(on_reject.get("qaState", "")) or "waiting"
            if semantic_key == "todo":
                return _parse_target(on_revalidate.get("qaState", "")) or "todo"

        return semantic_key


# Module-level convenience functions for backward compatibility
_cached_config: Optional[WorkflowConfig] = None


def _get_config(
    force_reload: bool = False,
    read_yaml_func: Any = None,
    file_exists_func: Any = None,
) -> WorkflowConfig:
    """Get or create the singleton WorkflowConfig instance.

    Args:
        force_reload: If True, create a new config instance
        read_yaml_func: Optional custom YAML reader (for testing)
        file_exists_func: Optional custom file existence checker (for testing)

    Returns:
        WorkflowConfig instance
    """
    global _cached_config
    if _cached_config is None or force_reload:
        _cached_config = WorkflowConfig()
    return _cached_config


def load_workflow_config(
    force_reload: bool = False,
    read_yaml_func: Any = None,
    file_exists_func: Any = None,
) -> Dict[str, Any]:
    """Load workflow configuration.

    Args:
        force_reload: If True, reload the configuration
        read_yaml_func: Optional custom YAML reader (for testing)
        file_exists_func: Optional custom file existence checker (for testing)

    Returns:
        Complete workflow configuration dict including:
        - validationLifecycle: Lifecycle transitions
        - timeouts: Timeout configuration
        - taskStates: List of task states (from state machine)
        - qaStates: List of QA states (from state machine)

    Raises:
        FileNotFoundError: If workflow.yaml or state-machine.yaml not found
        ValueError: If configuration is invalid
    """
    # Handle test dependency injection
    if read_yaml_func is not None or file_exists_func is not None:
        # For testing: directly load with injected dependencies
        if file_exists_func and not file_exists_func("config", "workflow.yaml"):
            raise FileNotFoundError("workflow.yaml not found in edison.data.config")

        try:
            if read_yaml_func:
                raw_config = read_yaml_func("config", "workflow.yaml")
            else:
                raw_config = real_read_yaml("config", "workflow.yaml")
        except Exception as e:
            raise ValueError(f"Failed to parse workflow.yaml: {e}")

        # Validate structure
        if not raw_config:
            raise ValueError("workflow.yaml is empty")

        forbidden_keys = [k for k in ("qaStates", "taskStates") if k in raw_config]
        if forbidden_keys:
            raise ValueError(
                "workflow.yaml must not define state lists (qaStates/taskStates); "
                "they are sourced from state-machine.yaml"
            )

        required_keys = ["validationLifecycle", "timeouts"]
        for key in required_keys:
            if key not in raw_config:
                raise ValueError(f"workflow.yaml missing required key: {key}")

        # Load state machine states
        if read_yaml_func:
            sm = read_yaml_func("config", "state-machine.yaml") or {}
        else:
            sm = real_read_yaml("config", "state-machine.yaml") or {}

        statemachine = sm.get("statemachine", {})

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

        return {
            **raw_config,
            "taskStates": task_states,
            "qaStates": qa_states,
        }

    # Production code: use cached config
    config = _get_config(force_reload=force_reload)
    return {
        "validationLifecycle": config.validation_lifecycle,
        "timeouts": config.timeouts,
        "taskStates": config.task_states,
        "qaStates": config.qa_states,
    }


def get_task_states(force_reload: bool = False) -> List[str]:
    """Get allowed task states from state machine configuration.

    Args:
        force_reload: If True, reload the configuration

    Returns:
        List of task state names
    """
    return _get_config(force_reload=force_reload).task_states


def get_qa_states(force_reload: bool = False) -> List[str]:
    """Get allowed QA states from state machine configuration.

    Args:
        force_reload: If True, reload the configuration

    Returns:
        List of QA state names
    """
    return _get_config(force_reload=force_reload).qa_states


def get_semantic_state(domain: str, semantic_key: str) -> str:
    """Resolve a semantic state to the configured state name.

    Args:
        domain: Either "task" or "qa"
        semantic_key: Semantic state name (e.g., "validated", "wip", "waiting")

    Returns:
        The configured state name for the semantic key
    """
    return _get_config().get_semantic_state(domain, semantic_key)


__all__ = [
    "WorkflowConfig",
    "load_workflow_config",
    "get_task_states",
    "get_qa_states",
    "get_semantic_state",
]




