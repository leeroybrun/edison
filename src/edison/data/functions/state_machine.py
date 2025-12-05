"""
State machine functions for dynamic content generation.

These functions read from workflow.yaml config (merged state machine).
Available via {{fn:...}} in templates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_state_machine_config() -> dict[str, Any]:
    """Load state machine configuration from workflow.yaml."""
    # First try workflow.yaml (merged location)
    workflow_path = Path(__file__).parent.parent / "config" / "workflow.yaml"
    if workflow_path.exists():
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f) or {}
            # State machine is under workflow.statemachine
            return {"statemachine": workflow.get("workflow", {}).get("statemachine", {})}
    return {}


def _get_domain_config(domain: str) -> dict[str, Any]:
    """Get configuration for a specific domain (task, qa, session)."""
    config = _load_state_machine_config()
    statemachine = config.get("statemachine", {})
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
        description = info.get("description", "")
        initial = " (initial)" if info.get("initial") else ""
        final = " (final)" if info.get("final") else ""
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
        description = info.get("description", "")
        initial = " (initial)" if info.get("initial") else ""
        final = " (final)" if info.get("final") else ""
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
        description = info.get("description", "")
        initial = " (initial)" if info.get("initial") else ""
        final = " (final)" if info.get("final") else ""
        result.append(f"- **{state}**{initial}{final}: {description}")

    return "\n".join(result)


def state_transitions(domain: str = "task") -> str:
    """Return valid transitions for a domain as markdown table.

    Args:
        domain: One of 'task', 'qa', or 'session'

    Returns:
        Markdown table showing valid transitions.
    """
    domain_config = _get_domain_config(domain)
    states_config = domain_config.get("states", {})

    # Build header
    header = "| From State | To State | Guard | Conditions |"
    separator = "|------------|----------|-------|------------|"
    rows = [header, separator]

    # Build rows
    for from_state, info in states_config.items():
        transitions = info.get("allowed_transitions", [])
        for trans in transitions:
            to_state = trans.get("to", "")
            guard = trans.get("guard", "")
            conditions = trans.get("conditions", [])
            cond_names = ", ".join(c.get("name", "") for c in conditions)
            rows.append(f"| {from_state} | {to_state} | {guard} | {cond_names} |")

    return "\n".join(rows)


def state_diagram(domain: str = "task") -> str:
    """Return mermaid diagram for state machine.

    Args:
        domain: One of 'task', 'qa', or 'session'

    Returns:
        Mermaid state diagram code.
    """
    domain_config = _get_domain_config(domain)
    states_config = domain_config.get("states", {})

    lines = ["```mermaid", "stateDiagram-v2"]

    # Find initial and final states
    initial_state = None
    final_states = []

    for state, info in states_config.items():
        if info.get("initial"):
            initial_state = state
        if info.get("final"):
            final_states.append(state)

    # Add initial transition
    if initial_state:
        lines.append(f"    [*] --> {initial_state}")

    # Add transitions
    for from_state, info in states_config.items():
        transitions = info.get("allowed_transitions", [])
        for trans in transitions:
            to_state = trans.get("to", "")
            lines.append(f"    {from_state} --> {to_state}")

    # Add final transitions
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
