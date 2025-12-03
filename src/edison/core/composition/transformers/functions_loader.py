"""Dynamic function loader for the template engine.

Loads Python callables from layered ``functions`` folders:
- Core:            <data>/functions/
- Bundled packs:   <data>/packs/<pack>/functions/
- Project packs:   .edison/packs/<pack>/functions/
- Project:         .edison/functions/

Functions are registered into the global FunctionRegistry and become
available to templates via ``{{function:name(args)}}`` through
FunctionTransformer.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Optional

from edison.core.composition.core.paths import CompositionPathResolver
from .functions import global_registry


def _iter_function_files(dirs: Iterable[Path]) -> Iterable[Path]:
    """Yield all ``*.py`` files from existing directories in order."""
    for d in dirs:
        if not d or not d.exists():
            continue
        for path in sorted(d.glob("*.py")):
            if path.is_file():
                yield path


def _load_module(path: Path) -> Optional[ModuleType]:
    """Dynamically load a module from file without adding to sys.modules."""
    spec = importlib.util.spec_from_file_location(f"edison.functions.{path.stem}", path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module
    return None


def load_functions(project_root: Optional[Path], active_packs: List[str]) -> None:
    """Load and register functions from all layers.

    Later layers override earlier ones (project > project packs > bundled packs > core).
    """
    resolver = CompositionPathResolver(project_root)

    dirs_in_order: List[Path] = [
        resolver.core_dir / "functions",
        *(resolver.bundled_packs_dir / p / "functions" for p in active_packs),
        *(resolver.project_packs_dir / p / "functions" for p in active_packs),
        resolver.project_dir / "functions",
    ]

    for path in _iter_function_files(dirs_in_order):
        module = _load_module(path)
        if not module:
            continue
        for name in dir(module):
            if name.startswith("_"):
                continue
            func = getattr(module, name)
            if callable(func):
                # Later layers overwrite earlier ones by simply re-adding the same name
                global_registry.add(name, func)


__all__ = ["load_functions"]
