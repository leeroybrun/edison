"""Agent roster generator.

Generates AVAILABLE_AGENTS.md from AgentRegistry data.
Uses ComposableRegistry with context_vars for {{#each}} expansion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Dict, List

from ..registries._base import ComposableRegistry


def _utc_timestamp() -> str:
    """Generate UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class AgentRosterGenerator(ComposableRegistry[str]):
    """Generator for AVAILABLE_AGENTS.md.
    
    Uses ComposableRegistry composition with agent data 
    via context_vars for {{#each agents}} expansion.
    
    Template: data/generators/AVAILABLE_AGENTS.md
    Output: _generated/AVAILABLE_AGENTS.md
    """
    
    content_type: ClassVar[str] = "generators"
    file_pattern: ClassVar[str] = "AVAILABLE_AGENTS.md"
    
    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        """Provide agent data for template expansion."""
        from edison.core.registries.agents import AgentRegistry
        from dataclasses import asdict
        
        registry = AgentRegistry(project_root=self.project_root)
        agents = registry.get_all()
        
        return {
            "agents": [asdict(a) for a in agents],
            "generated_at": _utc_timestamp(),
        }
    
    def write(self, output_dir: Path) -> Path:
        """Compose and write AVAILABLE_AGENTS.md.
        
        Args:
            output_dir: Directory for output file
            
        Returns:
            Path to written file
        """
        packs = self.get_active_packs()
        content = self.compose("AVAILABLE_AGENTS", packs)
        
        if not content:
            raise FileNotFoundError(
                f"Template 'AVAILABLE_AGENTS.md' not found in {self.content_type}/"
            )
        
        output_path = output_dir / "AVAILABLE_AGENTS.md"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.writer.write_text(output_path, content)
        return output_path


__all__ = ["AgentRosterGenerator"]

