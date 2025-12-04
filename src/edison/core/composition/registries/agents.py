#!/usr/bin/env python3
"""Edison Agent Registry.

Thin wrapper around ComposableRegistry for agent composition.
ALL discovery and composition is handled by the unified composition system.

Agent-specific features:
- Constitution header injection
- Front matter metadata extraction

Architecture:
    CompositionBase → ComposableRegistry → AgentRegistry
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from .base import ComposableRegistry
from edison.core.utils.text import render_conditional_includes
from ..utils.paths import resolve_project_dir_placeholders


class AgentError(RuntimeError):
    """Base error for agent composition."""


class AgentNotFoundError(AgentError):
    """Raised when a requested agent does not exist."""


class AgentRegistry(ComposableRegistry[str]):
    """Registry for discovering and composing Edison agents.

    Extends ComposableRegistry with agent-specific:
    - Constitution header injection
    - Front matter metadata extraction
    """

    content_type: ClassVar[str] = "agents"
    file_pattern: ClassVar[str] = "*.md"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": True,
        "enable_dedupe": False,
        "enable_template_processing": True,
    }

    # ------- Constitution Header (agent-specific) -------

    def _build_constitution_header(self) -> str:
        """Build constitution reference header for agent prompts."""
        return """## MANDATORY: Read Constitution First

Before starting any work, you MUST read the Agent Constitution at:
`{{PROJECT_EDISON_DIR}}/_generated/constitutions/AGENTS.md`

This constitution contains:
- Your mandatory workflow
- Applicable rules you must follow
- Output format requirements
- All mandatory guideline reads

**Re-read the constitution:**
- At the start of every task
- After any context compaction
- When instructed by the orchestrator

---"""

    # ------- Agent-Specific Post-Processing -------

    def _post_compose(self, name: str, content: str) -> str:
        """Apply agent-specific post-processing."""
        packs = self.get_active_packs()

        # Conditional includes
        if packs:
            content = render_conditional_includes(content, packs)

        # Constitution header
        header = self._build_constitution_header()
        content = f"{header}\n\n{content}"

        # Resolve placeholders
        target_path = self.project_dir / "_generated" / "agents" / f"{name}.md"
        content = resolve_project_dir_placeholders(
            content,
            project_dir=self.project_dir,
            target_path=target_path,
            repo_root=self.project_root,
        )

        return content

    # ------- Front Matter Metadata (agent-specific) -------

    @staticmethod
    def _read_front_matter(path: Path) -> Dict[str, Any]:
        """Extract YAML front matter from an agent file."""
        from edison.core.utils.text import parse_frontmatter

        try:
            text = path.read_text(encoding="utf-8").lstrip("\ufeff")
            doc = parse_frontmatter(text)
            return doc.frontmatter
        except Exception:
            return {}

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Get metadata for a single agent."""
        paths = self.discover_core()
        if name not in paths:
            return {"name": name, "type": "implementer", "model": "codex", "description": ""}

        fm = self._read_front_matter(paths[name])
        return {
            "name": name,
            "type": fm.get("type", "implementer"),
            "model": fm.get("model", "codex"),
            "description": fm.get("description", ""),
        }

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all core agents."""
        return [self.get_metadata(name) for name in sorted(self.discover_core().keys())]

    # ------- DRY Report (agent-specific) -------

    def dry_duplicate_report_for_agent(
        self,
        agent_name: str,
        packs: List[str],
        *,
        dry_min_shingles: int = 2,
    ) -> Dict[str, Any]:
        """Generate DRY duplicate report for agent content.

        Analyzes content from core, pack overlays, and project overlays
        to detect potential duplicate content across layers.

        Args:
            agent_name: Name of the agent to analyze
            packs: List of active pack names
            dry_min_shingles: Minimum shingles for duplicate detection

        Returns:
            Dict with counts and violations/duplicates
        """
        from edison.core.utils.text import dry_duplicate_report

        # Gather content from each layer
        layers = self._gather_layers(agent_name, packs)

        # Organize by source type
        core_text = ""
        packs_text = ""
        overlay_text = ""

        for layer in layers:
            if layer.source == "core":
                core_text = layer.content
            elif layer.source.startswith("pack:"):
                packs_text += "\n\n" + layer.content
            elif layer.source == "project":
                overlay_text = layer.content

        # Generate DRY report
        return dry_duplicate_report(
            {"core": core_text, "packs": packs_text.strip(), "overlay": overlay_text},
            min_shingles=dry_min_shingles,
        )


def compose_agent(
    agent_name: str,
    packs: List[str],
    *,
    project_root: Optional[Path] = None,
) -> str:
    """Functional wrapper for composing a single agent."""
    registry = AgentRegistry(project_root=project_root)
    result = registry.compose(agent_name, packs)
    if result is None:
        raise AgentNotFoundError(f"Agent '{agent_name}' not found")
    return result


__all__ = [
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "compose_agent",
]
