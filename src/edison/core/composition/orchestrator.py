from __future__ import annotations

"""Orchestrator discovery helpers.

Provides agent and pack discovery functions used by registries.
All legacy manifest/Claude composition functions have been removed -
use the unified composition engine instead.
"""

from pathlib import Path
from typing import Dict, List, Iterable, Set

from edison.core.utils import io as io_utils
from .packs import yaml
from .validators import collect_validators
from .workflow import get_workflow_loop_instructions


def collect_agents(repo_root: Path, packs_dir: Path, active_packs: List[str], project_dir: Path) -> Dict[str, List[str]]:
    """Collect agents from Core + Packs + Project using AgentRegistry.
    
    Uses unified AgentRegistry for all discovery - no manual globs.
    """
    from . import agents as agents_module

    AgentRegistry = agents_module.AgentRegistry

    registry = AgentRegistry(repo_root=repo_root)
    # Ensure project overlays resolve to the provided project_dir during tests
    registry.project_dir = project_dir
    agents: Dict[str, List[str]] = {
        "generic": [],
        "specialized": [],
        "project": [],
    }

    core_agents = registry.discover_core_agents()
    generic_names = sorted(core_agents.keys())
    agents["generic"] = generic_names

    specialized_set: Set[str] = set()
    for name in generic_names:
        overlays = registry.discover_pack_overlays(name, active_packs)
        if overlays:
            specialized_set.add(name)

    for name in registry.discover_pack_agent_names(active_packs):
        if name not in core_agents:
            specialized_set.add(name)

    agents["specialized"] = sorted(specialized_set)

    # Use unified discovery for project agents - no manual glob
    project_names: List[str] = []
    existing_names = set(core_agents.keys())
    
    # Get agents with project overlays
    for name in generic_names:
        if registry.project_overlay_path(name) is not None:
            project_names.append(name)
    
    # Get project-new agents via unified discovery
    project_new = registry._composer.discover_project_new(existing_names)
    for name in project_new:
        if name not in project_names:
            project_names.append(name)

    agents["project"] = sorted(project_names)
    return agents


def collect_packs(packs_dir: Path, active_packs: Iterable[str]) -> List[Dict[str, str]]:
    """Return metadata for active packs (id, name, version).

    Falls back to sensible defaults if pack.yml is missing or PyYAML is unavailable.
    """

    packs: List[Dict[str, str]] = []
    for pack_name in active_packs:
        base_meta = {
            "id": str(pack_name),
            "name": str(pack_name).replace("-", " ").title(),
            "version": "0.0.0",
        }

        pack_yml = packs_dir / pack_name / "pack.yml"
        if pack_yml.exists() and yaml is not None:
            data = io_utils.read_yaml(pack_yml, default={})
            meta_block = data.get("pack") or {}
            if isinstance(meta_block, dict):
                base_meta["id"] = str(meta_block.get("id") or base_meta["id"])
                base_meta["name"] = str(meta_block.get("name") or base_meta["name"])
                base_meta["version"] = str(meta_block.get("version") or base_meta["version"])

        packs.append(base_meta)

    return packs


__all__ = [
    "collect_agents",
    "collect_packs",
    "collect_validators",
    "get_workflow_loop_instructions",
]
