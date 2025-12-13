"""Dynamic function loader for the template engine.

Loads Python callables from layered ``functions`` folders:
- Core:            core/composition/functions/
- Bundled packs:   data/packs/<pack>/functions/
- Project packs:   .edison/packs/<pack>/functions/
- Project:         .edison/functions/

Functions are registered into the global FunctionRegistry and become
available to templates via ``{{function:name(args)}}`` through
FunctionTransformer.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from edison.core.composition.core.paths import CompositionPathResolver
from edison.core.utils.loader import (
    build_layer_dirs,
    iter_python_files,
    load_module_from_path,
    register_callables_from_module,
)
from .functions import global_registry

# Core functions directory (relative to this file's parent - core/composition/)
_CORE_FUNCTIONS_DIR = Path(__file__).parent.parent / "functions"


def load_functions(project_root: Optional[Path], active_packs: List[str]) -> None:
    """Load and register functions from all layers.

    Later layers override earlier ones (project > project packs > bundled packs > core).
    """
    resolver = CompositionPathResolver(project_root)

    dirs_in_order = build_layer_dirs(
        core_dir=_CORE_FUNCTIONS_DIR,
        content_type="",  # Functions are directly in the functions/ directory
        bundled_packs_dir=resolver.bundled_packs_dir,
        project_packs_dir=resolver.project_packs_dir,
        project_dir=resolver.project_dir,
        active_packs=active_packs,
    )
    
    # Adjust paths: for packs and project, add "functions" subdirectory
    # The build_layer_dirs with content_type="" gives us the base dirs,
    # but we need to append "functions" for all except core (which is already functions/)
    adjusted_dirs: List[Path] = [_CORE_FUNCTIONS_DIR]
    for pack in active_packs:
        adjusted_dirs.append(resolver.bundled_packs_dir / pack / "functions")
    for pack in active_packs:
        adjusted_dirs.append(resolver.project_packs_dir / pack / "functions")
    adjusted_dirs.append(resolver.project_dir / "functions")

    for path in iter_python_files(adjusted_dirs):
        module = load_module_from_path(path, "edison.functions")
        if module:
            register_callables_from_module(module, global_registry.add)


__all__ = ["load_functions"]
