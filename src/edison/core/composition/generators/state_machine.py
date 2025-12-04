"""State machine document generator.

Generates STATE_MACHINE.md from state machine configuration.
Uses ComposableRegistry with context_vars for {{#each}} expansion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ..registries._base import ComposableRegistry


def _utc_timestamp() -> str:
    """Generate UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


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


class StateMachineGenerator(ComposableRegistry[str]):
    """Generator for STATE_MACHINE.md.
    
    Uses ComposableRegistry composition with state machine data
    via context_vars for {{#each}} expansion.
    
    Loads state machine config from SessionConfig domain.
    
    Template: data/generators/STATE_MACHINE.md
    Output: _generated/STATE_MACHINE.md
    """
    
    content_type: ClassVar[str] = "generators"
    file_pattern: ClassVar[str] = "STATE_MACHINE.md"
    
    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        """Provide state machine data for template expansion."""
        from edison.core.config.domains import SessionConfig
        
        session_cfg = SessionConfig(repo_root=self.project_root)
        statemachine = session_cfg._state_config
        
        # Build sources list
        sources = ["state-machine.yaml (bundled defaults)"]
        project_path = self.project_dir / "config" / "state-machine.yaml"
        if project_path.exists():
            sources.append("state-machine.yaml (project config)")
        
        # Build domains data for template
        domains = []
        for domain_name, spec in statemachine.items():
            states_config = (spec or {}).get("states") or {}
            
            # Build states list
            states = []
            for state_name, meta in states_config.items():
                meta = meta or {}
                states.append({
                    "name": state_name,
                    "description": meta.get("description", ""),
                    "initial": _format_bool(bool(meta.get("initial"))),
                    "final": _format_bool(bool(meta.get("final"))),
                })
            
            # Build transitions list
            transitions = []
            for from_state, meta in states_config.items():
                for transition in (meta or {}).get("allowed_transitions") or []:
                    to_state = transition.get("to", "")
                    guard = transition.get("guard") or "-"
                    conditions = _format_conditions(transition.get("conditions"))
                    actions = _format_actions(transition.get("actions"))
                    transitions.append({
                        "from": from_state,
                        "to": to_state,
                        "guard": guard if guard != "-" else "",
                        "conditions": conditions,
                        "actions": actions,
                    })
            
            domains.append({
                "name": domain_name,
                "title": domain_name.title(),
                "states": states,
                "transitions": transitions,
            })
        
        return {
            "sources": sources,
            "domains": domains,
            "generated_at": _utc_timestamp(),
        }
    
    def write(self, output_dir: Path) -> Path:
        """Compose and write STATE_MACHINE.md.
        
        Args:
            output_dir: Directory for output file
            
        Returns:
            Path to written file
        """
        packs = self.get_active_packs()
        content = self.compose("STATE_MACHINE", packs)
        
        if not content:
            raise FileNotFoundError(
                f"Template 'STATE_MACHINE.md' not found in {self.content_type}/"
            )
        
        output_path = output_dir / "STATE_MACHINE.md"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.writer.write_text(output_path, content)
        return output_path


__all__ = ["StateMachineGenerator"]
