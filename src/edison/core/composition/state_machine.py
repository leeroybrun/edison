"""Generate STATE_MACHINE.md from YAML configuration.

Relies exclusively on ``state-machine.yaml`` (core + project overlays) so
the rendered documentation always reflects the configured state machines.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from edison.core.config import ConfigManager

from .headers import build_generated_header
from .path_utils import resolve_project_dir_placeholders


def _state_machine_paths(cfg_mgr: ConfigManager) -> Tuple[Path, Optional[Path]]:
    """Return core + project state machine YAML paths."""
    core_path = cfg_mgr.core_config_dir / "state-machine.yaml"
    project_path = cfg_mgr.project_config_dir / "state-machine.yaml"
    return core_path, project_path if project_path.exists() else None


def _load_state_machine(cfg_mgr: ConfigManager) -> Dict[str, Any]:
    """Load and validate the merged state machine configuration."""
    core_path, project_path = _state_machine_paths(cfg_mgr)

    if not core_path.exists():
        raise FileNotFoundError(f"Missing state machine config at {core_path}")

    core_cfg = cfg_mgr.load_yaml(core_path)
    merged_cfg = dict(core_cfg)

    if project_path:
        project_cfg = cfg_mgr.load_yaml(project_path)
        merged_cfg = cfg_mgr.deep_merge(merged_cfg, project_cfg)

    cfg_mgr.validate_schema(merged_cfg, "state-machine-rich.schema.json")

    statemachine = merged_cfg.get("statemachine") or {}
    if not statemachine:
        raise ValueError("statemachine section required in state-machine.yaml")

    return statemachine


def _format_bool(value: bool) -> str:
    return "✅" if value else ""


def _format_conditions(conditions: Optional[List[Dict[str, Any]]]) -> str:
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
    for state_name, meta in states.items():
        description = (meta or {}).get("description", "")
        initial = _format_bool(bool((meta or {}).get("initial")))
        final = _format_bool(bool((meta or {}).get("final")))
        yield f"| {state_name} | {description} | {initial} | {final} |"


def _transition_rows(states: Dict[str, Any]) -> Iterable[str]:
    for from_state, meta in states.items():
        transitions = (meta or {}).get("allowed_transitions") or []
        for transition in transitions:
            to_state = transition.get("to", "")
            guard = transition.get("guard") or "-"
            conditions = _format_conditions(transition.get("conditions"))
            actions = _format_actions(transition.get("actions"))
            yield f"| {from_state} | {to_state} | {guard} | {conditions} | {actions} |"


def _mermaid_block(statemachine: Dict[str, Any]) -> str:
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
    states = (spec or {}).get("states") or {}

    parts: List[str] = [f"## {domain.title()} Domain", "", "### States", "", "| State | Description | Initial | Final |", "| ----- | ----------- | ------- | ----- |"]
    parts.extend(_state_rows(states))

    parts.extend(["", "### Transitions", "", "| From | To | Guard | Conditions | Actions |", "| ---- | -- | ----- | ---------- | ------- |"])
    transition_rows = list(_transition_rows(states))
    if transition_rows:
        parts.extend(transition_rows)
    else:
        parts.append("| - | - | - | - | - |")

    return "\n".join(parts)


def generate_state_machine_doc(output_path: Path, repo_root: Optional[Path] = None) -> None:
    """Render the configured state machine to Markdown."""
    cfg_mgr = ConfigManager(repo_root=repo_root)
    statemachine = _load_state_machine(cfg_mgr)
    core_path, project_path = _state_machine_paths(cfg_mgr)

    header = build_generated_header("state_machine", config=cfg_mgr, target_path=output_path)

    source_lines = ["- Source: state-machine.yaml (core config)"]
    if project_path:
        source_lines.append("- Overlay: state-machine.yaml (project config)")

    content_parts: List[str] = [
        header.strip(),
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    full_text = "\n".join(content_parts).strip() + "\n"
    project_dir = cfg_mgr.project_config_dir.parent
    full_text = resolve_project_dir_placeholders(
        full_text,
        project_dir=project_dir,
        target_path=output_path,
        repo_root=cfg_mgr.repo_root,
    )
    output_path.write_text(full_text, encoding="utf-8")


__all__ = ["generate_state_machine_doc"]
