"""Helper functions for agent composition tests.

NOTE: Core agents come from bundled edison.data package, not from .edison/core/.
These helpers create pack overlays and project-level customizations only.
"""
from __future__ import annotations

from pathlib import Path


def write_pack_overlay(root: Path, pack: str, agent: str) -> Path:
    """Create a minimal pack overlay using unified HTML comment syntax.
    
    Pack overlays extend bundled core agents with additional content.
    They are placed in .edison/packs/{pack}/agents/overlays/{agent}.md
    """
    pack_overlays_dir = root / ".edison" / "packs" / pack / "agents" / "overlays"
    pack_overlays_dir.mkdir(parents=True, exist_ok=True)
    path = pack_overlays_dir / f"{agent}.md"
    # Use unified HTML comment markers for section extensions
    content = "\n".join(
        [
            f"<!-- EXTEND: Tools -->",
            f"- {pack} specific tool",
            f"<!-- /EXTEND -->",
            "",
            f"<!-- EXTEND: Guidelines -->",
            f"- {pack} specific guideline",
            f"<!-- /EXTEND -->",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path


def write_project_agent(root: Path, name: str) -> Path:
    """Create a project-level agent (new agent defined at project level)."""
    project_agents_dir = root / ".edison" / "agents"
    project_agents_dir.mkdir(parents=True, exist_ok=True)
    path = project_agents_dir / f"{name}.md"
    content = "\n".join(
        [
            "---",
            f"name: {name}",
            "description: Project-level agent",
            "model: codex",
            "---",
            "",
            f"# Agent: {name}",
            "",
            "## Role",
            f"Project role for {name}.",
            "",
            "## Tools",
            "- Project tool",
            "",
            "## Guidelines",
            "- Project guideline",
            "",
            "## Workflows",
            "- Project workflow step",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path
