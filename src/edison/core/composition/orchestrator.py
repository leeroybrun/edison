from __future__ import annotations

"""Orchestrator discovery helpers.

Provides agent and pack discovery functions used by registries.
Uses the unified composition system for all discovery operations.
"""

from pathlib import Path
from typing import Dict, List, Iterable, Set

from edison.core.utils import io as io_utils
from .packs import yaml
from .validators import collect_validators


def collect_agents(
    repo_root: Path,
    packs_dir: Path,
    active_packs: List[str],
    project_dir: Path,
) -> Dict[str, List[str]]:
    """Collect agents from Core + Packs + Project using AgentRegistry.

    Uses unified AgentRegistry for all discovery - no manual globs.

    Args:
        repo_root: Project root path
        packs_dir: Packs directory (for backward compat, not used)
        active_packs: List of active pack names
        project_dir: Project config directory (for backward compat, not used)

    Returns:
        Dict with keys: generic (core), specialized (pack overlays/new), project
    """
    from .registries.agents import AgentRegistry

    registry = AgentRegistry(project_root=repo_root)

    agents: Dict[str, List[str]] = {
        "generic": [],
        "specialized": [],
        "project": [],
    }

    # Core agents (generic)
    core_agents = registry.discover_core()
    agents["generic"] = sorted(core_agents.keys())

    # Discover all entities across layers
    all_entities = registry.discover_all(active_packs)
    core_names = set(core_agents.keys())

    # Specialized: pack-new or pack-overlaid agents
    specialized_set: Set[str] = set()
    pack_entities = registry.discover_packs(active_packs)
    specialized_set.update(pack_entities.keys())

    # Also check for core agents with pack overlays
    for name in core_names:
        if name in all_entities and all_entities[name] != core_agents.get(name):
            specialized_set.add(name)

    agents["specialized"] = sorted(specialized_set)

    # Project: new project entities or project overlays
    project_entities = registry.discover_project()
    project_names: Set[str] = set(project_entities.keys())

    # Also include core/pack agents with project overlays
    for name in all_entities:
        # If it's in all but path differs from core/pack, it has project overlay
        if name not in project_names:
            core_path = core_agents.get(name)
            pack_path = pack_entities.get(name)
            all_path = all_entities.get(name)
            if all_path and all_path != core_path and all_path != pack_path:
                project_names.add(name)

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
]
