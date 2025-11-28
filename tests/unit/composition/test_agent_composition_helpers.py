"""Helper functions for agent composition tests."""
from __future__ import annotations

from pathlib import Path


def write_core_agent(root: Path, name: str) -> Path:
    """Create a minimal core agent template with unified placeholders."""
    core_agents_dir = root / ".edison" / "core" / "agents"
    core_agents_dir.mkdir(parents=True, exist_ok=True)
    path = core_agents_dir / f"{name}.md"
    # Use unified section placeholders
    content = "\n".join(
        [
            f"# Agent: {name}",
            "",
            "## Role",
            f"Core role for {name}.",
            "",
            "## Tools",
            "{{SECTION:Tools}}",
            "",
            "## Guidelines",
            "{{SECTION:Guidelines}}",
            "",
            "{{EXTENSIBLE_SECTIONS}}",
            "",
            "{{APPEND_SECTIONS}}",
            "",
            "## Workflows",
            "- Core workflow step",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path


def write_pack_overlay(root: Path, pack: str, agent: str) -> Path:
    """Create a minimal pack overlay using unified HTML comment syntax."""
    # Overlays must be in the overlays/ subdirectory (unified convention)
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
