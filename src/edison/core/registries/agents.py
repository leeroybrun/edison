"""Agent metadata registry.

Provides read-only access to agent metadata from YAML frontmatter.
This is separate from composition - it only reads metadata, not composed content.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity.base import EntityId
from edison.core.composition.core.paths import CompositionPathResolver
from edison.core.config.domains.packs import PacksConfig
from edison.core.packs.paths import iter_pack_dirs
from edison.core.utils.text import parse_frontmatter

from ._base import BaseRegistry


@dataclass
class AgentMetadata:
    """Agent metadata extracted from YAML frontmatter."""
    
    name: str
    type: str  # implementer, orchestrator, reviewer, etc.
    model: str  # codex, claude, etc.
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AgentRegistry(BaseRegistry[AgentMetadata]):
    """Registry for agent metadata.
    
    Reads agent metadata from YAML frontmatter in agent markdown files.
    Does NOT compose agents - use GenericRegistry for composition.
    
    Example:
        registry = AgentRegistry(project_root)
        agents = registry.get_all()
        for agent in agents:
            print(f"{agent.name}: {agent.description}")
    """
    
    entity_type: str = "agent"
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize agent registry.
        
        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        super().__init__(project_root)
        self._resolver = CompositionPathResolver(self.project_root, "agents")
        self._cache: Optional[Dict[str, AgentMetadata]] = None
    
    def _discover_agents(self) -> Dict[str, Path]:
        """Discover all agent files.
        
        Returns:
            Dict mapping agent name to file path
        """
        agents: Dict[str, Path] = {}
        
        # Core agents from bundled data
        core_dir = self._resolver.core_dir / "agents"
        if core_dir.exists():
            for path in core_dir.glob("*.md"):
                if path.name != "README.md":
                    agents[path.stem] = path

        # Pack-provided agents (bundled packs + project packs) for active packs only.
        #
        # Note: overlays live under agents/overlays/ and are not registrable entities.
        try:
            active_packs = PacksConfig(repo_root=self.project_root).active_packs
        except Exception:
            active_packs = []

        for _pack_name, pack_dir, _kind in iter_pack_dirs(self.project_root, packs=active_packs):
            pack_agents_dir = pack_dir / "agents"
            if not pack_agents_dir.exists():
                continue
            for path in pack_agents_dir.glob("*.md"):
                # New pack-defined agents must not shadow core agents.
                agents.setdefault(path.stem, path)

        # Project-defined agents (rare; most projects use overlays). Must not shadow existing.
        project_agents_dir = self._resolver.project_dir / "agents"
        if project_agents_dir.exists():
            for path in project_agents_dir.glob("*.md"):
                agents.setdefault(path.stem, path)
        
        return agents
    
    def _read_frontmatter(self, path: Path) -> Dict[str, Any]:
        """Extract YAML frontmatter from an agent file.
        
        Args:
            path: Path to agent markdown file
            
        Returns:
            Frontmatter dict or empty dict if not found
        """
        try:
            text = path.read_text(encoding="utf-8").lstrip("\ufeff")
            doc = parse_frontmatter(text)
            return doc.frontmatter
        except Exception:
            return {}
    
    def _load_all(self) -> Dict[str, AgentMetadata]:
        """Load all agent metadata (cached).
        
        Returns:
            Dict mapping agent name to metadata
        """
        if self._cache is not None:
            return self._cache
        
        self._cache = {}
        for name, path in self._discover_agents().items():
            fm = self._read_frontmatter(path)
            self._cache[name] = AgentMetadata(
                name=name,
                type=fm.get("type", "implementer"),
                model=fm.get("model", "codex"),
                description=fm.get("description", ""),
            )
        
        return self._cache
    
    def exists(self, entity_id: EntityId) -> bool:
        """Check if an agent exists.
        
        Args:
            entity_id: Agent name
            
        Returns:
            True if agent exists
        """
        return entity_id in self._load_all()
    
    def get(self, entity_id: EntityId) -> Optional[AgentMetadata]:
        """Get agent metadata by name.
        
        Args:
            entity_id: Agent name
            
        Returns:
            AgentMetadata if found, None otherwise
        """
        return self._load_all().get(entity_id)
    
    def get_all(self) -> List[AgentMetadata]:
        """Get all agent metadata.
        
        Returns:
            List of all agent metadata, sorted by name
        """
        return sorted(self._load_all().values(), key=lambda a: a.name)
    
    def list_names(self) -> List[str]:
        """List all agent names.
        
        Returns:
            Sorted list of agent names
        """
        return sorted(self._load_all().keys())


__all__ = ["AgentRegistry", "AgentMetadata"]
