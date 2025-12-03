"""Generate STATE_MACHINE.md from YAML configuration.

Reads state machine definitions from:
1. Bundled defaults: edison.data/config/state-machine.yaml
2. Project overrides: .edison/config/state-machine.yaml (merged on top)

The rendered documentation always reflects the actual configured state machines.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from edison.core.config import ConfigManager
from edison.core.composition.output.writer import CompositionFileWriter

from .headers import build_generated_header
from ..path_utils import resolve_project_dir_placeholders


def _state_machine_paths(cfg_mgr: ConfigManager) -> Tuple[Path, Optional[Path]]:
    """Return bundled + project state machine YAML paths."""
    # Bundled config from edison.data package
    bundled_path = cfg_mgr.core_config_dir / "state-machine.yaml"
    # Project-specific overrides
    project_path = cfg_mgr.project_config_dir / "state-machine.yaml"
    return bundled_path, project_path if project_path.exists() else None


def _load_state_machine(cfg_mgr: ConfigManager) -> Dict[str, Any]:
    """Load and validate the merged state machine configuration."""
    bundled_path, project_path = _state_machine_paths(cfg_mgr)

    if not bundled_path.exists():
        raise FileNotFoundError(f"Missing bundled state machine config at {bundled_path}")

    bundled_cfg = cfg_mgr.load_yaml(bundled_path)
    merged_cfg = dict(bundled_cfg)

    if project_path:
        project_cfg = cfg_mgr.load_yaml(project_path)
        merged_cfg = cfg_mgr.deep_merge(merged_cfg, project_cfg)

    # Validate against schema (silently skips if schema not found)
    cfg_mgr.validate_schema(merged_cfg, "config/state-machine-rich.schema.json")

    statemachine = merged_cfg.get("statemachine") or {}
    if not statemachine:
        raise ValueError("statemachine section required in state-machine.yaml")

    return statemachine


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


def generate_state_machine_doc(output_path: Path, repo_root: Optional[Path] = None) -> Path:
    """Render the configured state machine to Markdown.

    Args:
        output_path: Where to write the STATE_MACHINE.md file
        repo_root: Optional repository root (auto-detected if not provided)

    Returns:
        Path to the written file
    """
    cfg_mgr = ConfigManager(repo_root=repo_root)
    statemachine = _load_state_machine(cfg_mgr)
    bundled_path, project_path = _state_machine_paths(cfg_mgr)

    header = build_generated_header("state_machine", config=cfg_mgr, target_path=output_path)

    source_lines = ["- Source: state-machine.yaml (bundled defaults)"]
    if project_path:
        source_lines.append("- Overlay: state-machine.yaml (project config)")

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

    for domain, spec in statemachine.items():
        content_parts.append(_render_domain(domain, spec))
        content_parts.append("")

    full_text = "\n".join(content_parts).strip() + "\n"

    # Resolve placeholders
    project_dir = cfg_mgr.project_config_dir.parent
    full_text = resolve_project_dir_placeholders(
        full_text,
        project_dir=project_dir,
        target_path=output_path,
        repo_root=cfg_mgr.repo_root,
    )

    # Use CompositionFileWriter for unified file writing
    writer = CompositionFileWriter(base_dir=cfg_mgr.repo_root)
    writer.write_text(output_path, full_text)

    return output_path


__all__ = ["generate_state_machine_doc"]



