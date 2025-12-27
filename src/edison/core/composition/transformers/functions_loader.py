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
    build_layer_dirs_from_resolver,
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

    # Use the shared layered-loader helper so the function search path stays
    # consistent with other extensibility surfaces (guards/actions/parsers/etc).
    dirs = build_layer_dirs_from_resolver(
        core_dir=_CORE_FUNCTIONS_DIR.parent,
        content_type="functions",
        resolver=resolver,
        active_packs=active_packs,
    )

    for path in iter_python_files(dirs):
        module = load_module_from_path(path, "edison.functions")
        if module:
            register_callables_from_module(module, global_registry.add)


__all__ = ["load_functions"]
