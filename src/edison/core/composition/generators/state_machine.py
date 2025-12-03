"""State machine document generator.

Generates STATE_MACHINE.md from YAML configuration.

Unlike roster generators, StateMachineGenerator:
- Has NO template (renders directly from YAML)
- Overrides generate() to render markdown from state machine config
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .base import ComposableGenerator


def _format_bool(value: bool) -> str:
    """Format boolean as emoji for Markdown tables."""
    return "✅" if value else ""


def _format_conditions(conditions: Optional[List[Dict[str, Any]]]) -> str:
    """Format conditions list for Markdown tables."""
    if not conditions:
        return "-"

    def _render(cond: Dict[str, Any]) -> str:
        name = cond.get("name", "").strip()
        error = cond.get("error")
        nested = cond.get("or") or []
        parts: List[str] = []
        if name:
            parts.append(name)
        if error:
            parts.append(f"error: {error}")
        if nested:
            nested_parts = " OR ".join(_render(c) for c in nested)
            parts.append(f"({nested_parts})")
        return " ".join(parts) if parts else "-"

    return "; ".join(_render(c) for c in conditions)


def _format_actions(actions: Optional[List[Dict[str, Any]]]) -> str:
    """Format actions list for Markdown tables."""
    if not actions:
        return "-"

    def _render(action: Dict[str, Any]) -> str:
        name = action.get("name", "").strip()
        when = action.get("when")
        if when is None or when == "":
            return name or "-"
        return f"{name} (when: {when})" if name else f"when: {when}"

    return "; ".join(_render(a) for a in actions)


def _state_rows(states: Dict[str, Any]) -> Iterable[str]:
    """Generate Markdown table rows for states."""
    for state_name, meta in states.items():
        description = (meta or {}).get("description", "")
        initial = _format_bool(bool((meta or {}).get("initial")))
        final = _format_bool(bool((meta or {}).get("final")))
        yield f"| {state_name} | {description} | {initial} | {final} |"


def _transition_rows(states: Dict[str, Any]) -> Iterable[str]:
    """Generate Markdown table rows for transitions."""
    for from_state, meta in states.items():
        transitions = (meta or {}).get("allowed_transitions") or []
        for transition in transitions:
            to_state = transition.get("to", "")
            guard = transition.get("guard") or "-"
            conditions = _format_conditions(transition.get("conditions"))
            actions = _format_actions(transition.get("actions"))
            yield f"| {from_state} | {to_state} | {guard} | {conditions} | {actions} |"


def _mermaid_block(statemachine: Dict[str, Any]) -> str:
    """Generate Mermaid stateDiagram-v2 block."""
    lines: List[str] = ["```mermaid", "stateDiagram-v2"]
    for domain, spec in statemachine.items():
        lines.append(f"    state {domain.title()} {{")
        states = (spec or {}).get("states") or {}
        for from_state, meta in states.items():
            for transition in (meta or {}).get("allowed_transitions") or []:
                to_state = transition.get("to", "")
                label = transition.get("guard") or ""
                edge = f"        {from_state} --> {to_state}"
                if label:
                    edge = f"{edge} : {label}"
                lines.append(edge)
        lines.append("    }")
    lines.append("```")
    return "\n".join(lines)


def _render_domain(domain: str, spec: Dict[str, Any]) -> str:
    """Render a single domain's documentation section."""
    states = (spec or {}).get("states") or {}

    parts: List[str] = [
        f"## {domain.title()} Domain",
        "",
        "### States",
        "",
        "| State | Description | Initial | Final |",
        "| ----- | ----------- | ------- | ----- |",
    ]
    parts.extend(_state_rows(states))

    parts.extend([
        "",
        "### Transitions",
        "",
        "| From | To | Guard | Conditions | Actions |",
        "| ---- | -- | ----- | ---------- | ------- |",
    ])
    transition_rows = list(_transition_rows(states))
    if transition_rows:
        parts.extend(transition_rows)
    else:
        parts.append("| - | - | - | - | - |")

    return "\n".join(parts)


class StateMachineGenerator(ComposableGenerator):
    """Generate STATE_MACHINE.md from YAML configuration.

    Unlike other generators, this has NO template - it renders directly
    from the state machine YAML configuration.
    """

    @property
    def template_name(self) -> Optional[str]:
        return None  # No template - renders from config

    @property
    def output_filename(self) -> str:
        return "STATE_MACHINE.md"

    def _gather_data(self) -> Dict[str, Any]:
        """Load state machine configuration from YAML.

        Returns:
            Dictionary with:
            - statemachine: State machine configuration
            - bundled_path: Path to bundled config
            - project_path: Path to project config (if exists)
        """
        # Load state machine configuration
        bundled_path = self.core_dir / "config" / "state-machine.yaml"
        project_path = self.project_dir / "config" / "state-machine.yaml"

        if not bundled_path.exists():
            raise FileNotFoundError(f"Missing bundled state machine config at {bundled_path}")

        # Load bundled config
        bundled_cfg = self.cfg_mgr.load_yaml(bundled_path)
        merged_cfg = dict(bundled_cfg)

        # Merge with project config if exists
        if project_path.exists():
            project_cfg = self.cfg_mgr.load_yaml(project_path)
            merged_cfg = self.cfg_mgr.deep_merge(merged_cfg, project_cfg)

        # Validate statemachine section exists
        statemachine = merged_cfg.get("statemachine") or {}
        if not statemachine:
            raise ValueError("statemachine section required in state-machine.yaml")

        return {
            "statemachine": statemachine,
            "bundled_path": bundled_path,
            "project_path": project_path if project_path.exists() else None,
        }

    def generate(self) -> str:
        """Override generate to render directly from YAML config.

        Returns:
            Rendered STATE_MACHINE.md content
        """
        from datetime import datetime, timezone
        from edison.core.composition.output.headers import build_generated_header
        from ..path_utils import resolve_project_dir_placeholders

        # Load data
        data = self._gather_data()
        statemachine = data["statemachine"]
        project_path = data["project_path"]

        # Build header
        output_path = Path("STATE_MACHINE.md")  # Placeholder for header generation
        header = build_generated_header("state_machine", config=self.cfg_mgr, target_path=output_path)

        # Build source lines
        source_lines = ["- Source: state-machine.yaml (bundled defaults)"]
        if project_path:
            source_lines.append("- Overlay: state-machine.yaml (project config)")

        # Build content
        content_parts: List[str] = [
            header.strip(),
            "",
            "# State Machine",
            "",
            "This document is generated from the YAML state machine configuration.",
            "Do not edit manually; update the YAML config and re-run `edison compose`.",
            "",
            "## Sources",
            "",
            *source_lines,
            "",
            "## Diagram",
            "",
            _mermaid_block(statemachine),
            "",
            "## Domains",
            "",
        ]

        # Render each domain
        for domain, spec in statemachine.items():
            content_parts.append(_render_domain(domain, spec))
            content_parts.append("")

        full_text = "\n".join(content_parts).strip() + "\n"

        # Resolve placeholders
        full_text = resolve_project_dir_placeholders(
            full_text,
            project_dir=self.project_dir,
            target_path=output_path,
            repo_root=self.project_root,
        )

        return full_text


__all__ = [
    "StateMachineGenerator",
]
