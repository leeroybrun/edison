"""
State machine functions for dynamic content generation.

These functions read from WorkflowConfig (unified source of truth).
Available via {{function:name(args)}} in templates.
"""
from __future__ import annotations

from typing import Any


def _get_workflow_config() -> Any:
    """Get WorkflowConfig instance for state machine access."""
    from edison.core.config.domains.workflow import WorkflowConfig
    return WorkflowConfig()


def _get_domain_config(domain: str) -> dict[str, Any]:
    """Get configuration for a specific domain (task, qa, session)."""
    wf_cfg = _get_workflow_config()
    statemachine = wf_cfg._statemachine
    return statemachine.get(domain, {})


def task_states() -> str:
    """Return task states from config as markdown list.

    Returns:
        Markdown formatted list of task states with descriptions.
    """
    domain_config = _get_domain_config("task")
    states_config = domain_config.get("states", {})

    result = []
    for state, info in states_config.items():
        description = info.get("description", "") if isinstance(info, dict) else ""
        initial = " (initial)" if isinstance(info, dict) and info.get("initial") else ""
        final = " (final)" if isinstance(info, dict) and info.get("final") else ""
        result.append(f"- **{state}**{initial}{final}: {description}")

    return "\n".join(result)


def qa_states() -> str:
    """Return QA states from config as markdown list.

    Returns:
        Markdown formatted list of QA states with descriptions.
    """
    domain_config = _get_domain_config("qa")
    states_config = domain_config.get("states", {})

    result = []
    for state, info in states_config.items():
        description = info.get("description", "") if isinstance(info, dict) else ""
        initial = " (initial)" if isinstance(info, dict) and info.get("initial") else ""
        final = " (final)" if isinstance(info, dict) and info.get("final") else ""
        result.append(f"- **{state}**{initial}{final}: {description}")

    return "\n".join(result)


def session_states() -> str:
    """Return session states from config as markdown list.

    Returns:
        Markdown formatted list of session states with descriptions.
    """
    domain_config = _get_domain_config("session")
    states_config = domain_config.get("states", {})

    result = []
    for state, info in states_config.items():
        description = info.get("description", "") if isinstance(info, dict) else ""
        initial = " (initial)" if isinstance(info, dict) and info.get("initial") else ""
        final = " (final)" if isinstance(info, dict) and info.get("final") else ""
        result.append(f"- **{state}**{initial}{final}: {description}")

    return "\n".join(result)


def state_transitions(domain: str = "task") -> str:
    """Return valid transitions for a domain as markdown table.

    Args:
        domain: One of 'task', 'qa', or 'session'

    Returns:
        Markdown table showing valid transitions.
    """
    wf_cfg = _get_workflow_config()
    transitions = wf_cfg.get_transitions(domain)

    # Build header
    header = "| From State | To State | Guard | Conditions |"
    separator = "|------------|----------|-------|------------|"
    rows = [header, separator]

    # Build rows
    for from_state, to_states in transitions.items():
        for to_state in to_states:
            trans = wf_cfg.get_transition(domain, from_state, to_state)
            guard = trans.get("guard", "") if trans else ""
            conditions = trans.get("conditions", []) if trans else []
            cond_names = ", ".join(c.get("name", "") for c in conditions if isinstance(c, dict))
            rows.append(f"| {from_state} | {to_state} | {guard} | {cond_names} |")

    return "\n".join(rows)


def state_diagram(domain: str = "task") -> str:
    """Return mermaid diagram for state machine.

    Args:
        domain: One of 'task', 'qa', or 'session'

    Returns:
        Mermaid state diagram code.
    """
    wf_cfg = _get_workflow_config()

    lines = ["```mermaid", "stateDiagram-v2"]

    # Get initial and final states
    try:
        initial_state = wf_cfg.get_initial_state(domain)
        lines.append(f"    [*] --> {initial_state}")
    except ValueError:
        pass

    # Add transitions
    transitions = wf_cfg.get_transitions(domain)
    for from_state, to_states in transitions.items():
        for to_state in to_states:
            lines.append(f"    {from_state} --> {to_state}")

    # Add final transitions
    final_states = wf_cfg.get_final_states(domain)
    for final in final_states:
        lines.append(f"    {final} --> [*]")

    lines.append("```")

    return "\n".join(lines)


def all_states_overview() -> str:
    """Return an overview of all state machines.

    Returns:
        Markdown formatted overview of task, QA, and session states.
    """
    result = []

    result.append("## Task States")
    result.append(task_states())
    result.append("")

    result.append("## QA States")
    result.append(qa_states())
    result.append("")

    result.append("## Session States")
    result.append(session_states())

    return "\n".join(result)






