"""Domain-specific configuration for workflow lifecycle and state machine.

Provides cached access to workflow lifecycle configuration including
validation lifecycle transitions, timeouts, and state machine configuration.
This is the unified source of truth for all state/transition/recommendation config.
"""
from __future__ import annotations

from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple

from ..base import BaseDomainConfig


class WorkflowConfig(BaseDomainConfig):
    """Unified workflow and state machine configuration.

    Provides typed, cached access to workflow configuration including:
    - Validation lifecycle transitions
    - Workflow timeouts
    - State machine states, transitions, guards, recommendations, and rules

    This is the SINGLE SOURCE OF TRUTH for all state-related configuration.
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Pack overlays should not redefine workflow/state-machine mechanics, but this
    domain still uses the unified config cache to avoid accidental double-loading.
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

    # ===== STATE MACHINE ACCESS =====

    @cached_property
    def _statemachine(self) -> Dict[str, Any]:
        """Get state machine config section.
        
        Reads from workflow.statemachine (canonical location).
        """
        sm = self.section.get("statemachine", {})
        if isinstance(sm, dict) and sm:
            return sm
        
        raise ValueError("workflow.statemachine configuration section is missing")

    @cached_property
    def _state_machine_states(self) -> Tuple[List[str], List[str]]:
        """Load task and QA states from state machine config."""
        statemachine = self._statemachine

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

    @cached_property
    def session_states(self) -> List[str]:
        """Get allowed session states."""
        session_cfg = self._statemachine.get("session", {})
        states_cfg = session_cfg.get("states", {})
        if isinstance(states_cfg, dict):
            return list(states_cfg.keys())
        if isinstance(states_cfg, list):
            return [str(s) for s in states_cfg]
        return []

    @cached_property
    def plan_states(self) -> List[str]:
        """Get allowed plan states."""
        plan_cfg = self._statemachine.get("plan", {})
        states_cfg = plan_cfg.get("states", {})
        if isinstance(states_cfg, dict):
            return list(states_cfg.keys())
        if isinstance(states_cfg, list):
            return [str(s) for s in states_cfg]
        return []

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
            if semantic_key == "blocked":
                return "blocked"

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

        if domain == "session":
            # Session states are direct mappings
            return semantic_key

        return semantic_key

    def get_initial_state(self, domain: str) -> str:
        """Get the initial state for a domain.

        Args:
            domain: "task", "qa", or "session"

        Returns:
            The initial state name from config

        Raises:
            ValueError: If domain is unknown or no initial state found
        """
        domain_cfg = self._statemachine.get(domain, {})
        states_cfg = domain_cfg.get("states", {})

        # Look for state marked as initial=true
        if isinstance(states_cfg, dict):
            for state_name, state_meta in states_cfg.items():
                if isinstance(state_meta, dict) and state_meta.get("initial"):
                    return state_name

        # Fallback: first state in list
        states = self.get_states(domain)
        if states:
            return states[0]

        raise ValueError(f"No initial state found for domain: {domain}")

    def get_final_state(self, domain: str) -> str:
        """Get the final/validated state for a domain.

        Args:
            domain: "task", "qa", or "session"

        Returns:
            The final state name from config

        Raises:
            ValueError: If domain is unknown or no final state found
        """
        domain_cfg = self._statemachine.get(domain, {})
        states_cfg = domain_cfg.get("states", {})

        # Look for state marked as final=true
        if isinstance(states_cfg, dict):
            for state_name, state_meta in states_cfg.items():
                if isinstance(state_meta, dict) and state_meta.get("final"):
                    return state_name

        # Fallback to "validated" if no final state marked
        if domain in ("task", "qa", "session"):
            return "validated"

        raise ValueError(f"No final state found for domain: {domain}")

    def get_final_states(self, domain: str) -> List[str]:
        """Get all final states for a domain.

        Args:
            domain: "task", "qa", or "session"

        Returns:
            List of final state names
        """
        domain_cfg = self._statemachine.get(domain, {})
        states_cfg = domain_cfg.get("states", {})
        finals = []

        if isinstance(states_cfg, dict):
            for state_name, state_meta in states_cfg.items():
                if isinstance(state_meta, dict) and state_meta.get("final"):
                    finals.append(state_name)

        return finals if finals else ["validated"]

    def is_terminal_state(self, domain: str, state: str) -> bool:
        """Check if a state is terminal (final).

        Args:
            domain: "task", "qa", or "session"
            state: The state name to check

        Returns:
            True if the state is a final state
        """
        return state in self.get_final_states(domain)

    def get_states(self, domain: str) -> List[str]:
        """Get all states for a domain.

        Args:
            domain: "task", "qa", "session", or "plan"

        Returns:
            List of state names

        Raises:
            ValueError: If domain is unknown
        """
        if domain == "task":
            return self.task_states
        elif domain == "qa":
            return self.qa_states
        elif domain == "session":
            return self.session_states
        elif domain == "plan":
            return self.plan_states
        else:
            raise ValueError(f"Unknown domain: {domain}")

    # ===== TRANSITION ACCESS =====

    def get_transition(self, domain: str, from_state: str, to_state: str) -> Optional[Dict[str, Any]]:
        """Get transition config between two states.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name
            to_state: The target state name

        Returns:
            Transition config dict or None if no such transition exists
        """
        state_config = self._statemachine.get(domain, {}).get("states", {}).get(from_state, {})
        for trans in state_config.get("allowed_transitions", []):
            if trans.get("to") == to_state:
                return trans
        return None

    def get_transitions_from(self, domain: str, state: str) -> List[Dict[str, Any]]:
        """Get all allowed transitions from a state.

        Args:
            domain: "task", "qa", or "session"
            state: The source state name

        Returns:
            List of transition config dicts
        """
        state_config = self._statemachine.get(domain, {}).get("states", {}).get(state, {})
        return state_config.get("allowed_transitions", [])

    def get_recommendations(self, domain: str, from_state: str, to_state: str) -> List[Dict[str, Any]]:
        """Get recommendation actions for a transition.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name
            to_state: The target state name

        Returns:
            List of recommendation dicts with id, entity, rationale, blocking, cmd_template
        """
        trans = self.get_transition(domain, from_state, to_state)
        return trans.get("recommendations", []) if trans else []

    def get_transition_rules(self, domain: str, from_state: str, to_state: str) -> List[str]:
        """Get rule IDs for a transition.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name
            to_state: The target state name

        Returns:
            List of rule ID strings (e.g., ["RULE.GUARDS.FAIL_CLOSED"])
        """
        trans = self.get_transition(domain, from_state, to_state)
        return trans.get("rules", []) if trans else []

    def get_transition_guard(self, domain: str, from_state: str, to_state: str) -> Optional[str]:
        """Get guard name for a transition.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name
            to_state: The target state name

        Returns:
            Guard name string or None
        """
        trans = self.get_transition(domain, from_state, to_state)
        return trans.get("guard") if trans else None

    def get_transition_actions(self, domain: str, from_state: str, to_state: str) -> List[Dict[str, Any]]:
        """Get actions to execute for a transition.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name
            to_state: The target state name

        Returns:
            List of action dicts with name and optional when condition
        """
        trans = self.get_transition(domain, from_state, to_state)
        return trans.get("actions", []) if trans else []

    def get_transition_conditions(self, domain: str, from_state: str, to_state: str) -> List[Dict[str, Any]]:
        """Get conditions for a transition.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name
            to_state: The target state name

        Returns:
            List of condition dicts with name and optional error message
        """
        trans = self.get_transition(domain, from_state, to_state)
        return trans.get("conditions", []) if trans else []

    def get_all_recommendations_for_state(self, domain: str, from_state: str) -> List[Dict[str, Any]]:
        """Get all recommendations from a state to any target state.

        Args:
            domain: "task", "qa", or "session"
            from_state: The source state name

        Returns:
            List of all recommendation dicts from this state
        """
        all_recs = []
        for trans in self.get_transitions_from(domain, from_state):
            recs = trans.get("recommendations", [])
            for rec in recs:
                # Add target state info to each recommendation
                rec_with_target = {**rec, "_to_state": trans.get("to")}
                all_recs.append(rec_with_target)
        return all_recs

    # NOTE: Guidance rules are NOT configured in workflow.yaml.
    # They are defined in rules/registry.yml with `contexts: [guidance, ...]`
    # Use edison.core.session.next.rules.get_rules_for_context() to look them up.

    def get_transitions(self, domain: str) -> Dict[str, List[str]]:
        """Get transition map for a domain type.

        Returns a dict mapping each state to its list of allowed target states.
        This is used for simple state machine validation.

        Args:
            domain: "task", "qa", or "session"

        Returns:
            Dict mapping from_state to list of allowed to_states
        """
        result: Dict[str, List[str]] = {}
        states = self._statemachine.get(domain, {}).get("states", {})
        if isinstance(states, dict):
            for state_name, state_config in states.items():
                if isinstance(state_config, dict):
                    transitions = state_config.get("allowed_transitions", [])
                    result[state_name] = [t.get("to") for t in transitions if t.get("to")]
                else:
                    result[state_name] = []
        return result


__all__ = [
    "WorkflowConfig",
]




