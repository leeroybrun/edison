"""State machine documentation helpers (Phase 1B).

This module centralizes generation of:
- A transition matrix (Markdown table) for task, QA, and session domains.
- A Mermaid state diagram string.

It derives task/QA transitions from `.edison/core/config/defaults.yaml` and
session transitions from :mod:`sessionlib.STATE_TRANSITIONS`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from ..paths import PathResolver, EdisonPathError
from ..paths.project import get_project_config_dir
from ..file_io.utils import ensure_dir
from .config import SessionConfig


def _load_statemachine_spec() -> Dict[str, Any]:
    """Load task/QA state machine specification from core defaults."""
    try:
        # First try loading from project root (for project-specific overrides)
        root = PathResolver.resolve_project_root()
        defaults_path = get_project_config_dir(root, create=False) / "core" / "config" / "defaults.yaml"
        if defaults_path.exists():
            from edison.core.file_io.utils import read_yaml_safe
            data = read_yaml_safe(defaults_path, default={})
            return (data.get("statemachine") or {}) if isinstance(data, dict) else {}
    except EdisonPathError:
        pass

    # Fallback to packaged data
    try:
        from edison.data import read_yaml
        data = read_yaml("config", "defaults.yaml")
        return (data.get("statemachine") or {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _guard_description(domain: str, from_state: str, to_state: str) -> str:
    """Return a short human-readable description of guard conditions."""
    if domain == "task":
        if from_state == "todo" and to_state == "wip":
            return "Task must be claimed by session"
        if from_state == "wip" and to_state == "done":
            return "Implementation report required before promotion"
        if from_state == "done" and to_state == "validated":
            return "All blocking validators must pass"
        if from_state == "done" and to_state == "wip":
            return "Rollback requires explicit reason"
        return "Adjacent move (guarded by tasks CLI)"

    if domain == "qa":
        if from_state == "waiting" and to_state == "todo":
            return "Task must be done before QA starts"
        if from_state == "wip" and to_state == "done":
            return "Bundle approved & validator artefacts present"
        return "Adjacent move (guarded by QA CLI)"

    if domain == "session":
        if from_state == "active" and to_state == "closing":
            return "Closing requires validation readiness (no blockers)"
        if from_state == "closing" and to_state == "validated":
            return "All closing validations must succeed"
        if to_state == "recovery":
            return "Error or timeout triggers recovery"
        return "Transition guarded by session state machine"

    return ""


def _domain_transitions(domain_spec: Dict[str, Any]):
    """Yield (from_state, to_state) pairs from rich or legacy specs."""
    states = domain_spec.get("states") or {}
    if isinstance(states, dict):
        for from_state, info in states.items():
            for t in (info or {}).get("allowed_transitions", []) or []:
                to_state = t.get("to")
                if to_state:
                    yield str(from_state), str(to_state)
        return
    transitions = domain_spec.get("transitions") or {}
    for from_state, targets in (transitions or {}).items():
        for to_state in targets or []:
            yield str(from_state), str(to_state)


def generate_transition_matrix() -> str:
    """Generate a Markdown transition matrix for task, QA, and session domains."""
    sm = _load_statemachine_spec()
    lines: List[str] = [
        "| Domain | From | To | Guards |",
        "| ------ | ---- | -- | ------ |",
    ]

    # Task and QA from defaults.yaml
    for domain in ("task", "qa"):
        domain_spec = sm.get(domain) or {}
        for from_state, to_state in _domain_transitions(domain_spec):
            guard = _guard_description(domain, str(from_state), str(to_state))
            lines.append(f"| {domain} | {from_state} | {to_state} | {guard} |")

    # Session domain from SessionConfig
    session_transitions = SessionConfig().get_transitions("session")
    for from_state, targets in sorted((session_transitions or {}).items()):  # type: ignore[attr-defined]
        for to_state in targets:
            guard = _guard_description("session", from_state, to_state)
            lines.append(f"| session | {from_state} | {to_state} | {guard} |")

    return "\n".join(lines) + "\n"


def generate_mermaid_diagram() -> str:
    """Generate a Mermaid state diagram for the three domains."""
    sm = _load_statemachine_spec()
    lines: List[str] = ["stateDiagram-v2"]

    # Task domain
    task_spec = sm.get("task") or {}
    lines.append("    state Task {")
    for from_state, to_state in _domain_transitions(task_spec):
        label = _guard_description("task", str(from_state), str(to_state))
        if label:
            lines.append(f"        {from_state} --> {to_state} : {label}")
        else:
            lines.append(f"        {from_state} --> {to_state}")
    lines.append("    }")

    # QA domain
    qa_spec = sm.get("qa") or {}
    lines.append("    state QA {")
    for from_state, to_state in _domain_transitions(qa_spec):
        label = _guard_description("qa", str(from_state), str(to_state))
        if label:
            lines.append(f"        {from_state} --> {to_state} : {label}")
        else:
            lines.append(f"        {from_state} --> {to_state}")
    lines.append("    }")

    # Session domain
    lines.append("    state Session {")
    session_transitions = SessionConfig().get_transitions("session")
    for from_state, targets in sorted((session_transitions or {}).items()):  # type: ignore[attr-defined]
        for to_state in targets:
            label = _guard_description("session", from_state, to_state)
            if label:
                lines.append(f"        {from_state} --> {to_state} : {label}")
            else:
                lines.append(f"        {from_state} --> {to_state}")
    lines.append("    }")

    return "\n".join(lines) + "\n"


def write_state_machine_docs(target_path: Path | None = None) -> Path:
    """Write STATE_MACHINE.md documentation to the given path.

    When ``target_path`` is None, resolves to the core docs location under
    the current project root:

        <root>/.edison/core/docs/STATE_MACHINE.md
    """
    if target_path is None:
        try:
            root = PathResolver.resolve_project_root()
        except EdisonPathError:
            root = Path(__file__).resolve().parents[3]
        target_path = get_project_config_dir(root, create=False) / "core" / "docs" / "STATE_MACHINE.md"

    matrix = generate_transition_matrix()
    mermaid = generate_mermaid_diagram()

    content = [
        "# Edison State Machine",
        "",
        "This document is generated from the canonical state machine definitions",
        "in `.edison/core/config/defaults.yaml` (tasks/QA) and `SessionConfig`",
        "for session lifecycle.",
        "",
        "## Transition Matrix",
        "",
        matrix.rstrip(),
        "",
        "## Mermaid Diagram",
        "",
        "```mermaid",
        mermaid.rstrip(),
        "```",
        "",
        "## Guard Conditions (Summary)",
        "",
        "- **Task todo → wip**: Task must be claimed by session.",
        "- **Task wip → done**: Implementation report required before promotion.",
        "- **Task done → validated**: All blocking validators must pass.",
        "- **Task done → wip**: Requires explicit rollback reason.",
        "",
        "Additional QA and session guards are enforced by their respective",
        "CLIs; see `.edison/core/guidelines/orchestrators/STATE_MACHINE_GUARDS.md` for details.",
        "",
    ]

    ensure_dir(target_path.parent)
    target_path.write_text("\n".join(content), encoding="utf-8")
    return target_path


__all__ = [
    "generate_transition_matrix",
    "generate_mermaid_diagram",
    "write_state_machine_docs",
]
