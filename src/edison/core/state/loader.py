"""Dynamic handler loader for state machine guards, actions, and conditions.

Loads Python callables from layered folders:
- Core:            core/state/builtin/guards|actions|conditions/
- Bundled packs:   data/packs/<pack>/guards|actions|conditions/
- Project packs:   .edison/packs/<pack>/guards|actions|conditions/
- Project:         .edison/guards|actions|conditions/

Handlers are registered into their respective registries and become
available to the state machine for transition validation and execution.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from edison.core.utils.loader import (
    build_layer_dirs,
    iter_python_files,
    load_module_from_path,
    register_callables_from_module,
)

logger = logging.getLogger(__name__)

# Handler type identifiers
HANDLER_TYPES = ("guards", "actions", "conditions")

# Core handlers directory (relative to this file)
# Named "builtin" to avoid conflict with handlers.py (registry base classes)
_CORE_HANDLERS_DIR = Path(__file__).parent / "builtin"


def _get_layer_dirs(
    handler_type: str,
    bundled_packs_dir: Path,
    project_packs_dir: Path,
    project_dir: Path,
    active_packs: List[str],
) -> List[Path]:
    """Get directories for a handler type in layer order.
    
    Uses the core handlers directory (`core/state/builtin/`) as the first layer,
    then pack and project directories (layered override).
    """
    return build_layer_dirs(
        core_dir=_CORE_HANDLERS_DIR,
        content_type=handler_type,
        bundled_packs_dir=bundled_packs_dir,
        project_packs_dir=project_packs_dir,
        project_dir=project_dir,
        active_packs=active_packs,
    )


def load_guards(project_root: Optional[Path], active_packs: List[str]) -> int:
    """Load and register guards from all layers.
    
    Later layers override earlier ones (project > project packs > bundled packs > core).
    
    Returns:
        Number of guards loaded
    """
    from .guards import registry as guard_registry

    # Always load core builtin handlers, even when project_root cannot be resolved.
    # This prevents "Unknown guard/condition/action" failures in contexts where
    # AGENTS_PROJECT_ROOT is not set and CWD is not inside a git repo (common in tests).
    if project_root is None:
        dirs = [_CORE_HANDLERS_DIR / "guards"]
    else:
        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(project_root)
        dirs = _get_layer_dirs(
            "guards",
            resolver.bundled_packs_dir,
            resolver.project_packs_dir,
            resolver.project_dir,
            active_packs,
        )
    
    count = 0
    for path in iter_python_files(dirs):
        module = load_module_from_path(path, "edison.guards")
        if module:
            count += register_callables_from_module(module, guard_registry.add)
    
    return count


def load_actions(project_root: Optional[Path], active_packs: List[str]) -> int:
    """Load and register actions from all layers.
    
    Later layers override earlier ones (project > project packs > bundled packs > core).
    
    Returns:
        Number of actions loaded
    """
    from .actions import registry as action_registry

    if project_root is None:
        dirs = [_CORE_HANDLERS_DIR / "actions"]
    else:
        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(project_root)
        dirs = _get_layer_dirs(
            "actions",
            resolver.bundled_packs_dir,
            resolver.project_packs_dir,
            resolver.project_dir,
            active_packs,
        )
    
    count = 0
    for path in iter_python_files(dirs):
        module = load_module_from_path(path, "edison.actions")
        if module:
            count += register_callables_from_module(module, action_registry.add)
    
    return count


def load_conditions(project_root: Optional[Path], active_packs: List[str]) -> int:
    """Load and register conditions from all layers.
    
    Later layers override earlier ones (project > project packs > bundled packs > core).
    
    Returns:
        Number of conditions loaded
    """
    from .conditions import registry as condition_registry

    if project_root is None:
        dirs = [_CORE_HANDLERS_DIR / "conditions"]
    else:
        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(project_root)
        dirs = _get_layer_dirs(
            "conditions",
            resolver.bundled_packs_dir,
            resolver.project_packs_dir,
            resolver.project_dir,
            active_packs,
        )
    
    count = 0
    for path in iter_python_files(dirs):
        module = load_module_from_path(path, "edison.conditions")
        if module:
            count += register_callables_from_module(module, condition_registry.add)
    
    return count


def load_handlers(project_root: Optional[Path] = None, active_packs: Optional[List[str]] = None) -> dict:
    """Load all handler types (guards, actions, conditions) from all layers.
    
    Args:
        project_root: Project root path (auto-detected if None)
        active_packs: List of active pack names (loaded from config if None)
        
    Returns:
        Dict with counts of loaded handlers by type
    """
    # Resolve project root if not provided
    if project_root is None:
        try:
            from edison.core.utils.paths import PathResolver
            project_root = PathResolver.resolve_project_root()
        except Exception:
            project_root = None
    
    # Get active packs from config if not provided
    if active_packs is None:
        try:
            from edison.core.config import get_config
            cfg = get_config()
            packs_cfg = cfg.get("packs", {})
            active_packs = packs_cfg.get("active", []) if isinstance(packs_cfg, dict) else []
        except Exception:
            active_packs = []
    
    counts = {
        "guards": load_guards(project_root, active_packs),
        "actions": load_actions(project_root, active_packs),
        "conditions": load_conditions(project_root, active_packs),
    }
    
    total = sum(counts.values())
    if total > 0:
        logger.debug("Loaded %d handlers: %s", total, counts)
    
    return counts


__all__ = [
    "load_handlers",
    "load_guards",
    "load_actions",
    "load_conditions",
    "HANDLER_TYPES",
]
