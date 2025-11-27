#!/usr/bin/env python3
from __future__ import annotations

"""
Edison Agent Composition Engine

Thin wrapper around the core composition system for agents.
All discovery and composition logic is delegated to LayeredComposer.

Agent-specific responsibilities:
- Constitution header injection
- Conditional includes processing
- Front matter metadata extraction
- Roster generation

Uses the core composition system with HTML comment markers for overlays.

Architecture:
    BaseEntityManager
    └── BaseRegistry
        └── AgentRegistry (this module)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import BaseRegistry
from edison.core.utils.io import parse_yaml_string
from edison.core.utils.text import dry_duplicate_report, render_conditional_includes
from ..path_utils import resolve_project_dir_placeholders

# Import from core composition system - ALL discovery and composition
from ..core import (
    LayeredComposer,
    LayerSource,
    SectionParser,
    CompositionValidationError,
)


def compose(
    content_type: str,
    name: str,
    packs: List[str],
    repo_root: Optional[Path] = None,
) -> str:
    """Compose a single entity using the layered composition system."""
    composer = LayeredComposer(repo_root=repo_root, content_type=content_type)
    return composer.compose(name, packs)


class AgentError(RuntimeError):
    """Base error for agent composition."""


class AgentNotFoundError(AgentError):
    """Raised when a requested agent does not have a core template."""


class AgentTemplateError(AgentError):
    """Raised when a core agent template is structurally invalid."""


@dataclass
class CoreAgent:
    """Core agent reference (for backward compatibility)."""
    name: str
    core_path: Path
    
    @classmethod
    def from_layer_source(cls, source: LayerSource) -> "CoreAgent":
        """Create CoreAgent from unified LayerSource."""
        return cls(name=source.entity_name, core_path=source.path)


@dataclass
class PackOverlay:
    """Pack overlay reference (for backward compatibility)."""
    pack: str
    path: Path
    
    @classmethod
    def from_layer_source(cls, source: LayerSource) -> "PackOverlay":
        """Create PackOverlay from unified LayerSource."""
        # Extract pack name from layer string "pack:{name}"
        pack_name = source.layer.replace("pack:", "") if source.layer.startswith("pack:") else source.layer
        return cls(pack=pack_name, path=source.path)


class AgentRegistry(BaseRegistry[CoreAgent]):
    """Discover and compose Edison agents using the core composition system.
    
    Extends BaseRegistry with agent-specific functionality:
    - Constitution header injection
    - Conditional includes processing
    - Front matter metadata extraction
    
    ALL discovery is delegated to LayeredComposer.
    """
    
    entity_type: str = "agent"

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        super().__init__(repo_root)
        # Alias for compatibility
        self.repo_root = self.project_root
        
        # Use unified composer for ALL discovery
        self._composer = LayeredComposer(repo_root=self.project_root, content_type="agents")
    
    # ------- BaseRegistry Interface Implementation -------
    
    def discover_core(self) -> Dict[str, CoreAgent]:
        """Discover core agents via LayeredComposer."""
        sources = self._composer.discover_core()
        return {name: CoreAgent.from_layer_source(src) for name, src in sources.items()}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, CoreAgent]:
        """Discover agents from packs (both new and overlays)."""
        result: Dict[str, CoreAgent] = {}
        existing = set(self._composer.discover_core().keys())
        
        for pack in packs:
            # Get pack-new agents
            pack_new = self._composer.discover_pack_new(pack, existing)
            for name, source in pack_new.items():
                result[name] = CoreAgent.from_layer_source(source)
            existing.update(pack_new.keys())
        
        return result
    
    def discover_project(self) -> Dict[str, CoreAgent]:
        """Discover project-level agents."""
        existing = set(self._composer.discover_core().keys())
        project_new = self._composer.discover_project_new(existing)
        return {name: CoreAgent.from_layer_source(src) for name, src in project_new.items()}

    # ------- Discovery (delegated to unified system) ------- 
    
    def discover_core_agents(self) -> Dict[str, CoreAgent]:
        """Discover core agents via unified LayeredComposer.
        
        Alias for discover_core() for backward compatibility.
        """
        return self.discover_core()

    def resolve_core_agent(self, name: str) -> CoreAgent:
        """Resolve a specific core agent."""
        agents = self.discover_core()
        if name not in agents:
            raise AgentNotFoundError(
                f"Core agent '{name}' not found. Available: {sorted(agents.keys())}"
            )
        return agents[name]

    def exists(self, name: str) -> bool:
        """Check if an agent exists in the registry."""
        return name in self._composer.discover_core()

    def get(self, name: str) -> Optional[CoreAgent]:
        """Get an agent by name.
        
        Returns:
            CoreAgent if found, None otherwise
        """
        agents = self.discover_core()
        return agents.get(name)
    
    def get_metadata(self, name: str) -> Dict:
        """Get agent metadata dict by name.
        
        For backward compatibility with code expecting dict return.
        """
        agent = self.resolve_core_agent(name)
        return {
            "name": agent.name,
            "core_path": str(agent.core_path),
        }

    def discover_pack_overlays(self, agent_name: str, packs: List[str]) -> List[PackOverlay]:
        """Discover pack overlays for a given agent via unified system."""
        overlays: List[PackOverlay] = []
        existing = set(self._composer.discover_core().keys())
        
        for pack in packs:
            pack_overlays = self._composer.discover_pack_overlays(pack, existing)
            if agent_name in pack_overlays:
                overlays.append(PackOverlay.from_layer_source(pack_overlays[agent_name]))
            # Update existing for next pack (pack-new entities become existing)
            pack_new = self._composer.discover_pack_new(pack, existing)
            existing.update(pack_new.keys())
        
        return overlays

    def discover_pack_agent_names(self, packs: List[str]) -> List[str]:
        """Discover new agent names defined by packs (not overlays)."""
        names: List[str] = []
        existing = set(self._composer.discover_core().keys())
        
        for pack in packs:
            pack_new = self._composer.discover_pack_new(pack, existing)
            for name in pack_new:
                if name not in names:
                    names.append(name)
            existing.update(pack_new.keys())
        
        return names

    def project_overlay_path(self, agent_name: str) -> Optional[Path]:
        """Return project overlay path if it exists."""
        existing = set(self._composer.discover_core().keys())
        # Add pack entities to existing (project overlays can extend pack-new)
        # Note: This simplified version only checks core agents
        project_overlays = self._composer.discover_project_overlays(existing)
        if agent_name in project_overlays:
            return project_overlays[agent_name].path
        return None

    # ------- Constitution Reference (agent-specific) ------- 
    
    def _build_constitution_header(self) -> str:
        """Build the constitution reference header to inject at the top of agent prompts."""
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

    # ------- Composition (unified + agent post-processing) ------- 
    
    def compose_agent(self, agent_name: str, packs: List[str]) -> str:
        """Compose a single agent from core + pack + project overlays.
        
        Uses the unified composition system, then applies agent-specific post-processing.
        """
        # Use unified composition system for section-based composition
        try:
            composed = compose(
                content_type="agents",
                name=agent_name,
                packs=packs,
                repo_root=self.repo_root,
            )
        except CompositionValidationError as e:
            if "not found" in str(e).lower():
                raise AgentNotFoundError(str(e)) from e
            raise AgentError(str(e)) from e
        
        # Agent-specific post-processing
        if packs:
            composed = render_conditional_includes(composed, packs)
        
        constitution_header = self._build_constitution_header()
        composed = f"{constitution_header}\n\n{composed}"
        
        target_path = self.project_dir / "_generated" / "agents" / f"{agent_name}.md"
        composed = resolve_project_dir_placeholders(
            composed,
            project_dir=self.project_dir,
            target_path=target_path,
            repo_root=self.repo_root,
        )
        
        return composed

    # ------- DRY analysis (uses unified discovery) ------- 
    
    def dry_duplicate_report_for_agent(
        self,
        agent_name: str,
        packs: List[str],
        dry_min_shingles: Optional[int] = None,
    ) -> Dict:
        """Return DRY duplication report using unified discovery."""
        parser = SectionParser()
        
        def extract_content(text: str) -> str:
            sections = parser.parse(text)
            return "\n\n".join(s.content for s in sections if s.content.strip())
        
        # Get core content
        core_entities = self._composer.discover_core()
        if agent_name not in core_entities:
            raise AgentNotFoundError(f"Agent '{agent_name}' not found in core")
        core_text = core_entities[agent_name].path.read_text(encoding="utf-8")
        core_sections = extract_content(core_text) or core_text
        
        # Get pack overlay content
        existing = set(core_entities.keys())
        pack_chunks: List[str] = []
        for pack in packs:
            pack_overlays = self._composer.discover_pack_overlays(pack, existing)
            if agent_name in pack_overlays:
                text = pack_overlays[agent_name].path.read_text(encoding="utf-8")
                content = extract_content(text)
                if content:
                    pack_chunks.append(content)
            pack_new = self._composer.discover_pack_new(pack, existing)
            existing.update(pack_new.keys())
        packs_text = "\n\n".join(pack_chunks)
        
        # Get project overlay content
        overlay_text = ""
        project_overlays = self._composer.discover_project_overlays(existing)
        if agent_name in project_overlays:
            proj_text = project_overlays[agent_name].path.read_text(encoding="utf-8")
            overlay_text = extract_content(proj_text)
        
        # Get DRY config
        from edison.core.config import ConfigManager
        cfg = ConfigManager().load_config(validate=False)
        dry_config = cfg.get("composition", {}).get("dryDetection", {})
        min_s = dry_min_shingles if dry_min_shingles is not None else dry_config.get("minShingles", 2)
        k = dry_config.get("shingleSize", 12)
        
        return dry_duplicate_report(
            {"core": core_sections, "packs": packs_text, "overlay": overlay_text},
            min_shingles=min_s,
            k=k,
        )

    # ------- Roster metadata (agent-specific) ------- 
    
    @staticmethod
    def _read_front_matter(path: Path) -> Dict[str, Any]:
        """Extract YAML front matter from an agent file."""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return {}

        cleaned = text.lstrip("\ufeff")
        if not cleaned.startswith("---"):
            return {}

        parts = cleaned.split("---", 2)
        if len(parts) < 3:
            return {}

        data = parse_yaml_string(parts[1], default={})
        return data if isinstance(data, dict) else {}

    def get_all(self) -> List[CoreAgent]:
        """Return all core agents.
        
        Implements BaseRegistry interface.
        """
        return list(self.discover_core().values())
    
    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Return metadata for all core agents.
        
        For backward compatibility with code expecting list of metadata dicts.
        """
        agents: List[Dict[str, Any]] = []
        for core_agent in self.discover_core().values():
            meta = self._read_front_matter(core_agent.core_path)
            agents.append(
                {
                    "name": str(meta.get("name") or core_agent.name),
                    "type": str(meta.get("type") or "implementer"),
                    "model": str(meta.get("model") or "codex"),
                    "description": str(meta.get("description") or ""),
                    "core_path": str(core_agent.core_path),
                }
            )
        return sorted(agents, key=lambda a: a["name"])


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



