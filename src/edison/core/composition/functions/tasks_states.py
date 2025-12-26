"""
Utility functions available to the template engine via {{function:...}}.

Functions here are loaded by the layered functions loader:
- core functions (this file)
- pack functions (bundled packs/<pack>/functions)
- project pack functions (.edison/packs/<pack>/functions)
- project functions (.edison/functions)

All functions should be pure and return strings.

Uses WorkflowConfig as the single source of truth for state machine config.
"""
from __future__ import annotations

from typing import Any


def _get_workflow_config() -> Any:
    """Get WorkflowConfig instance for state machine access."""
    from edison.core.config.domains.workflow import WorkflowConfig
    return WorkflowConfig()


def _get_states(domain: str = "task") -> list[str]:
    """Get state names for a domain from config."""
    wf_cfg = _get_workflow_config()
    return wf_cfg.get_states(domain)


def _get_state_info(domain: str, state: str) -> dict[str, Any] | None:
    """Get detailed info for a specific state."""
    wf_cfg = _get_workflow_config()
    statemachine = wf_cfg._statemachine
    domain_config = statemachine.get(domain, {})
    states_config = domain_config.get("states", {})
    info = states_config.get(state)
    return info if isinstance(info, dict) else None


def tasks_states(state: str | None = None) -> str:
    """Return allowed task states or details for a specific state.

    Args:
        state: Optional state name. When provided, returns a single-line
            description. When omitted, returns a bullet list of all states.

    Returns:
        String formatted for markdown injection.
    """
    states = _get_states("task")

    if state:
        normalized = state.strip().lower()
        if normalized not in states:
            return f"Unknown task state: {state}"
        state_info = _get_state_info("task", normalized)
        if state_info:
            description = state_info.get("description", "No description")
            return f"{normalized}: {description}"
        return f"{normalized}: allowed transitions depend on project rules."

    # Return bullet list of all states with descriptions
    result = []
    for s in states:
        state_info = _get_state_info("task", s)
        if state_info:
            description = state_info.get("description", "")
            result.append(f"- **{s}**: {description}")
        else:
            result.append(f"- {s}")
    return "\n".join(result)











