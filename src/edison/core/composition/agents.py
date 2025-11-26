#!/usr/bin/env python3
from __future__ import annotations

"""
Edison Agent Composition Engine

Builds final agent prompts from layered sources:
  Core agent templates + Pack overlays + optional project overlays.

Discovery:
  - Core agents:      .edison/core/agents/*-core.md  (generic templates)
  - Pack overlays:    .edison/packs/<pack>/agents/<agent>.md
  - Project overlays: <project_config_dir>/agents/<agent>.md

The composed agent text is pure Markdown and typically written to
`<project_config_dir>/_generated/agents/<agent>.md` by the compose CLI.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import os

from ..utils.text import dry_duplicate_report, render_conditional_includes
from ..paths import PathResolver
from ..paths.project import get_project_config_dir


class AgentError(RuntimeError):
    """Base error for agent composition."""


class AgentNotFoundError(AgentError):
    """Raised when a requested agent does not have a core template."""


class AgentTemplateError(AgentError):
    """Raised when a core agent template is structurally invalid."""


@dataclass
class CoreAgent:
    name: str
    core_path: Path


@dataclass
class PackOverlay:
    pack: str
    path: Path


def _extract_sections(text: str) -> Tuple[str, str]:
    """Extract Tools and Guidelines sections from a Markdown document.

    Sections are detected by second‑level headings:
      - ``## Tools``
      - ``## Guidelines``
    Content is captured until the next heading line starting with ``#``.
    """
    tools_lines: List[str] = []
    guidelines_lines: List[str] = []
    current: Optional[str] = None

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            if heading == "tools":
                current = "tools"
                continue
            if heading == "guidelines":
                current = "guidelines"
                continue
            # Allow architecture sections to flow into guidelines so
            # critical architecture notes in overlays are preserved in
            # composed agent prompts.
            if heading.startswith("architecture"):
                current = "guidelines"
                continue
            current = None
            continue

        if current == "tools":
            tools_lines.append(line)
        elif current == "guidelines":
            guidelines_lines.append(line)

    tools = "\n".join(tools_lines).strip()
    guidelines = "\n".join(guidelines_lines).strip()
    # Fallback: when no structured sections are found, treat the whole text as
    # guidelines so pack/project overlays without headings still flow through
    # composition.
    if not tools and not guidelines:
        guidelines = text.strip()
    return tools, guidelines


class AgentRegistry:
    """Discover and compose Edison agents from Core + Packs + Project."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        # Respect project root resolution, including AGENTS_PROJECT_ROOT in tests
        self.repo_root: Path = repo_root or PathResolver.resolve_project_root()
        self.core_dir = self.repo_root / ".edison" / "core"
        self.packs_dir = self.repo_root / ".edison" / "packs"
        self.project_dir = get_project_config_dir(self.repo_root)

    # ------- Discovery -------
    def discover_core_agents(self) -> Dict[str, CoreAgent]:
        """Return mapping of agent name → CoreAgent from core templates."""
        agents: Dict[str, CoreAgent] = {}
        core_agents_dir = self.core_dir / "agents"
        if not core_agents_dir.exists():
            return agents

        for path in sorted(core_agents_dir.glob("*-core.md")):
            stem = path.stem
            if not stem.endswith("-core"):
                continue
            name = stem[: -len("-core")]
            agents[name] = CoreAgent(name=name, core_path=path)
        return agents

    def resolve_core_agent(self, name: str) -> CoreAgent:
        agents = self.discover_core_agents()
        if name not in agents:
            raise AgentNotFoundError(
                f"Core agent '{name}' not found under {self.core_dir / 'agents'}"
            )
        return agents[name]

    def discover_pack_overlays(self, agent_name: str, packs: List[str]) -> List[PackOverlay]:
        """Discover pack overlays for a given agent name."""
        overlays: List[PackOverlay] = []
        for pack in packs:
            overlay_path = self.packs_dir / pack / "agents" / f"{agent_name}.md"
            if overlay_path.exists():
                overlays.append(PackOverlay(pack=pack, path=overlay_path))
        return overlays

    def discover_pack_agent_names(self, packs: List[str]) -> List[str]:
        """Discover all agent names provided by packs (concrete agents only)."""
        names: List[str] = []
        for pack in packs:
            pack_agents_dir = self.packs_dir / pack / "agents"
            if not pack_agents_dir.exists():
                continue
            for agent_file in sorted(pack_agents_dir.glob("*.md")):
                stem = agent_file.stem
                # Skip core/context helpers; only surface concrete agents
                if stem.endswith("-core") or stem.endswith("-context"):
                    continue
                if stem not in names:
                    names.append(stem)
        return names

    def project_overlay_path(self, agent_name: str) -> Optional[Path]:
        """Return project overlay path when present.

        Supports both legacy and new overlay locations:
          - <project_config_dir>/agents/<agent>.md
          - <project_config_dir>/agents/overlays/<agent>-overlay.md
        """
        overlays_dir = self.project_dir / "agents" / "overlays"
        candidates = [
            overlays_dir / f"{agent_name}-overlay.md",
            self.project_dir / "agents" / f"{agent_name}.md",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    # ------- Composition -------
    def compose_agent(self, agent_name: str, packs: List[str]) -> str:
        """Compose a single agent from core + pack + project overlays."""
        core_agent = self.resolve_core_agent(agent_name)
        core_text = core_agent.core_path.read_text(encoding="utf-8")

        # Minimal structural validation: must start with an Agent header
        if not core_text.lstrip().startswith("# Agent:"):
            raise AgentTemplateError(
                f"Core agent template {core_agent.core_path} is missing '# Agent:' header"
            )

        overlays = self.discover_pack_overlays(agent_name, packs)
        project_overlay = self.project_overlay_path(agent_name)

        tools_blocks: List[str] = []
        guideline_blocks: List[str] = []

        # Pack overlays
        for overlay in overlays:
            text = overlay.path.read_text(encoding="utf-8")
            tools, guidelines = _extract_sections(text)
            if tools:
                tools_blocks.append(f"### {overlay.pack}\n\n{tools.strip()}")
            if guidelines:
                guideline_blocks.append(f"### {overlay.pack}\n\n{guidelines.strip()}")

        # Optional project overlay (third layer)
        if project_overlay is not None:
            proj_text = project_overlay.read_text(encoding="utf-8")
            proj_tools, proj_guidelines = _extract_sections(proj_text)
            if proj_tools:
                tools_blocks.append(f"### project\n\n{proj_tools.strip()}")
            if proj_guidelines:
                guideline_blocks.append(f"### project\n\n{proj_guidelines.strip()}")

        tools_block = "\n\n".join(b for b in tools_blocks if b).strip()
        guidelines_block = "\n\n".join(b for b in guideline_blocks if b).strip()

        packs_display = ", ".join(packs) if packs else ""

        substitutions = {
            "AGENT_NAME": agent_name,
            "PACK_NAME": packs_display,
            "TOOLS": tools_block,
            "PACK_TOOLS": tools_block,
            "GUIDELINES": guidelines_block,
            "PACK_GUIDELINES": guidelines_block,
        }

        composed = core_text
        for key, value in substitutions.items():
            composed = composed.replace(f"{{{{{key}}}}}", value)

        # Allow core templates to gate sections on pack presence via
        # {{include-if:has-pack(name):...}} directives.
        if packs:
            composed = render_conditional_includes(composed, packs)

        return composed

    # ------- DRY analysis -------
    def dry_duplicate_report_for_agent(
        self,
        agent_name: str,
        packs: List[str],
        dry_min_shingles: Optional[int] = None,
    ) -> Dict:
        """Return DRY duplication report between core, packs, and project overlay.

        Uses the same 12-word shingling strategy as validator/guideline
        composition to detect overlapping content between layers.
        """
        core_agent = self.resolve_core_agent(agent_name)
        core_text = core_agent.core_path.read_text(encoding="utf-8")
        core_tools, core_guidelines = _extract_sections(core_text)
        core_sections = "\n\n".join(
            [s for s in (core_tools, core_guidelines) if s]
        )

        overlays = self.discover_pack_overlays(agent_name, packs)
        pack_chunks: List[str] = []
        for overlay in overlays:
            text = overlay.path.read_text(encoding="utf-8")
            tools, guidelines = _extract_sections(text)
            if tools:
                pack_chunks.append(tools)
            if guidelines:
                pack_chunks.append(guidelines)
        packs_text = "\n\n".join(pack_chunks)

        overlay_text = ""
        project_overlay = self.project_overlay_path(agent_name)
        if project_overlay is not None:
            proj_text = project_overlay.read_text(encoding="utf-8")
            proj_tools, proj_guidelines = _extract_sections(proj_text)
            overlay_text = "\n\n".join(
                [s for s in (proj_tools, proj_guidelines) if s]
            )

        min_s = (
            int(os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))
            if dry_min_shingles is None
            else dry_min_shingles
        )

        return dry_duplicate_report(
            {"core": core_sections, "packs": packs_text, "overlay": overlay_text},
            min_shingles=min_s,
            k=12,
        )


def compose_agent(agent_name: str, packs: List[str], *, repo_root: Optional[Path] = None) -> str:
    """Functional wrapper for AgentRegistry.compose_agent."""
    registry = AgentRegistry(repo_root=repo_root)
    return registry.compose_agent(agent_name, packs)


__all__ = [
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "AgentTemplateError",
    "CoreAgent",
    "PackOverlay",
    "compose_agent",
]
