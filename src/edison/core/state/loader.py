"""Dynamic handler loader for state machine guards, actions, and conditions.

Loads Python callables from layered folders:
- Core:            <data>/guards|actions|conditions/
- Bundled packs:   <data>/packs/<pack>/guards|actions|conditions/
- Project packs:   .edison/packs/<pack>/guards|actions|conditions/
- Project:         .edison/guards|actions|conditions/

Handlers are registered into their respective registries and become
available to the state machine for transition validation and execution.
"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Optional, Callable, Any

logger = logging.getLogger(__name__)

# Handler type identifiers
HANDLER_TYPES = ("guards", "actions", "conditions")


def _iter_handler_files(dirs: Iterable[Path]) -> Iterable[Path]:
    """Yield all ``*.py`` files from existing directories in order."""
    for d in dirs:
        if not d or not d.exists():
            continue
        for path in sorted(d.glob("*.py")):
            if path.is_file() and path.stem != "__init__":
                yield path


def _load_module(path: Path, handler_type: str) -> Optional[ModuleType]:
    """Dynamically load a module from file without adding to sys.modules."""
    module_name = f"edison.{handler_type}.{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            return module
    except Exception as e:
        logger.warning("Failed to load %s module %s: %s", handler_type, path, e)
    return None


def _get_layer_dirs(
    resolver: "CompositionPathResolver",
    handler_type: str,
    active_packs: List[str],
) -> List[Path]:
    """Get directories for a handler type in layer order."""
    return [
        resolver.core_dir / handler_type,
        *(resolver.bundled_packs_dir / p / handler_type for p in active_packs),
        *(resolver.project_packs_dir / p / handler_type for p in active_packs),
        resolver.project_dir / handler_type,
    ]


def _register_from_module(
    module: ModuleType,
    register_fn: Callable[[str, Callable[..., Any]], None],
) -> int:
    """Register all public callables from a module.
    
    Args:
        module: Loaded Python module
        register_fn: Function to register handlers (e.g., registry.add)
        
    Returns:
        Number of handlers registered
    """
    count = 0
    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if callable(obj) and not isinstance(obj, type):
            # Later layers overwrite earlier ones by simply re-adding
            register_fn(name, obj)
            count += 1
    return count


def load_guards(project_root: Optional[Path], active_packs: List[str]) -> int:
    """Load and register guards from all layers.
    
    Later layers override earlier ones (project > project packs > bundled packs > core).
    
    Returns:
        Number of guards loaded
    """
    from edison.core.composition.core.paths import CompositionPathResolver
    from .guards import registry as guard_registry
    
    resolver = CompositionPathResolver(project_root)
    dirs = _get_layer_dirs(resolver, "guards", active_packs)
    
    count = 0
    for path in _iter_handler_files(dirs):
        module = _load_module(path, "guards")
        if module:
            count += _register_from_module(module, guard_registry.add)
    
    return count


def load_actions(project_root: Optional[Path], active_packs: List[str]) -> int:
    """Load and register actions from all layers.
    
    Later layers override earlier ones (project > project packs > bundled packs > core).
    
    Returns:
        Number of actions loaded
    """
    from edison.core.composition.core.paths import CompositionPathResolver
    from .actions import registry as action_registry
    
    resolver = CompositionPathResolver(project_root)
    dirs = _get_layer_dirs(resolver, "actions", active_packs)
    
    count = 0
    for path in _iter_handler_files(dirs):
        module = _load_module(path, "actions")
        if module:
            count += _register_from_module(module, action_registry.add)
    
    return count


def load_conditions(project_root: Optional[Path], active_packs: List[str]) -> int:
    """Load and register conditions from all layers.
    
    Later layers override earlier ones (project > project packs > bundled packs > core).
    
    Returns:
        Number of conditions loaded
    """
    from edison.core.composition.core.paths import CompositionPathResolver
    from .conditions import registry as condition_registry
    
    resolver = CompositionPathResolver(project_root)
    dirs = _get_layer_dirs(resolver, "conditions", active_packs)
    
    count = 0
    for path in _iter_handler_files(dirs):
        module = _load_module(path, "conditions")
        if module:
            count += _register_from_module(module, condition_registry.add)
    
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
