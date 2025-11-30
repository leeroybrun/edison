"""Domain-specific configuration for workflow lifecycle.

Provides cached access to workflow lifecycle configuration including
validation lifecycle transitions and timeouts.
"""
from __future__ import annotations

from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple

from ..base import BaseDomainConfig


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
        """Get workflow configuration from cached config.

        Uses self.section to access config["workflow"], then extracts
        the relevant fields (validationLifecycle, timeouts) and validates them.
        """
        workflow = {
            "validationLifecycle": self.section.get("validationLifecycle", {}),
            "timeouts": self.section.get("timeouts", {}),
        }
        self._validate_workflow_config(workflow)
        return workflow

    def _validate_workflow_config(self, config: Dict[str, Any]) -> None:
        """Validate the structure of the workflow configuration."""
        if not config:
            raise ValueError("workflow configuration is empty")

        forbidden_keys = [k for k in ("qaStates", "taskStates") if k in config]
        if forbidden_keys:
            raise ValueError(
                "workflow configuration must not define state lists (qaStates/taskStates); "
                "they are sourced from state-machine configuration"
            )

        required_keys = ["validationLifecycle", "timeouts"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"workflow configuration missing required key: {key}")

        if not isinstance(config["validationLifecycle"], dict):
            raise ValueError("validationLifecycle must be a dict")

        if not isinstance(config["timeouts"], dict):
            raise ValueError("timeouts must be a dict")

    @cached_property
    def _state_machine_states(self) -> Tuple[List[str], List[str]]:
        """Load task and QA states from state machine config."""
        statemachine = self._config.get("statemachine", {})
        if not isinstance(statemachine, dict) or not statemachine:
            raise ValueError("statemachine configuration section is missing")

        def _states(domain: str) -> List[str]:
            domain_cfg = statemachine.get(domain)
            if not isinstance(domain_cfg, dict):
                raise ValueError(f"statemachine.{domain} configuration is missing")
            states_cfg = domain_cfg.get("states")
            if isinstance(states_cfg, dict):
                return list(states_cfg.keys())
            if isinstance(states_cfg, list):
                return [str(s) for s in states_cfg]
            raise ValueError(f"statemachine.{domain}.states must be a dict or list")

        task_states = _states("task")
        qa_states = _states("qa")

        if not task_states or not qa_states:
            raise ValueError("statemachine must declare task and QA states")

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

    def get_initial_state(self, domain: str) -> str:
        """Get the initial state for a domain.

        Args:
            domain: Either "task" or "qa"

        Returns:
            The initial state name from config

        Raises:
            ValueError: If domain is unknown or no initial state found
        """
        statemachine = self._config.get("statemachine", {})
        if not isinstance(statemachine, dict):
            raise ValueError("statemachine configuration section is missing")

        domain_cfg = statemachine.get(domain, {})
        states_cfg = domain_cfg.get("states", {})

        # Look for state marked as initial=true
        if isinstance(states_cfg, dict):
            for state_name, state_meta in states_cfg.items():
                if isinstance(state_meta, dict) and state_meta.get("initial"):
                    return state_name

        # Fallback: first state in list
        states = self.task_states if domain == "task" else self.qa_states
        if states:
            return states[0]

        raise ValueError(f"No initial state found for domain: {domain}")

    def get_final_state(self, domain: str) -> str:
        """Get the final/validated state for a domain.

        Args:
            domain: Either "task" or "qa"

        Returns:
            The final state name from config

        Raises:
            ValueError: If domain is unknown or no final state found
        """
        statemachine = self._config.get("statemachine", {})
        if not isinstance(statemachine, dict):
            raise ValueError("statemachine configuration section is missing")

        domain_cfg = statemachine.get(domain, {})
        states_cfg = domain_cfg.get("states", {})

        # Look for state marked as final=true
        if isinstance(states_cfg, dict):
            for state_name, state_meta in states_cfg.items():
                if isinstance(state_meta, dict) and state_meta.get("final"):
                    return state_name

        # Fallback to "validated" if no final state marked
        if domain in ("task", "qa"):
            return "validated"

        raise ValueError(f"No final state found for domain: {domain}")

    def get_states(self, domain: str) -> List[str]:
        """Get all states for a domain.

        Args:
            domain: Either "task" or "qa"

        Returns:
            List of state names

        Raises:
            ValueError: If domain is unknown
        """
        if domain == "task":
            return self.task_states
        elif domain == "qa":
            return self.qa_states
        else:
            raise ValueError(f"Unknown domain: {domain}")


# Module-level convenience functions for backward compatibility
_cached_config: Optional[WorkflowConfig] = None


def _get_config(force_reload: bool = False) -> WorkflowConfig:
    """Get or create the singleton WorkflowConfig instance.

    Args:
        force_reload: If True, create a new config instance

    Returns:
        WorkflowConfig instance
    """
    global _cached_config
    if _cached_config is None or force_reload:
        _cached_config = WorkflowConfig()
    return _cached_config


def load_workflow_config(force_reload: bool = False) -> Dict[str, Any]:
    """Load workflow configuration.

    Args:
        force_reload: If True, reload the configuration

    Returns:
        Complete workflow configuration dict including:
        - validationLifecycle: Lifecycle transitions
        - timeouts: Timeout configuration
        - taskStates: List of task states (from state machine)
        - qaStates: List of QA states (from state machine)
    """
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


def get_initial_state(domain: str, force_reload: bool = False) -> str:
    """Get the initial state for a domain.

    Args:
        domain: Either "task" or "qa"
        force_reload: If True, reload the configuration

    Returns:
        The initial state name from config

    Raises:
        ValueError: If domain is unknown or no initial state found
    """
    return _get_config(force_reload=force_reload).get_initial_state(domain)


def get_final_state(domain: str, force_reload: bool = False) -> str:
    """Get the final/validated state for a domain.

    Args:
        domain: Either "task" or "qa"
        force_reload: If True, reload the configuration

    Returns:
        The final state name from config

    Raises:
        ValueError: If domain is unknown or no final state found
    """
    return _get_config(force_reload=force_reload).get_final_state(domain)


def get_states(domain: str, force_reload: bool = False) -> List[str]:
    """Get all states for a domain.

    Args:
        domain: Either "task" or "qa"
        force_reload: If True, reload the configuration

    Returns:
        List of state names

    Raises:
        ValueError: If domain is unknown
    """
    return _get_config(force_reload=force_reload).get_states(domain)


__all__ = [
    "WorkflowConfig",
    "load_workflow_config",
    "get_task_states",
    "get_qa_states",
    "get_semantic_state",
    "get_initial_state",
    "get_final_state",
    "get_states",
]




