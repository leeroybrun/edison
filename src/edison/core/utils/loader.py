"""Common layered module loading utilities.

Provides shared utilities for loading Python modules from layered directories
following Edison's extensibility pattern:
- Core modules (bundled with Edison)
- Bundled pack modules (data/packs/<pack>/)
- Project pack modules (.edison/packs/<pack>/)
- Project modules (.edison/)

Later layers override earlier ones, allowing customization at any level.
"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def build_layer_dirs(
    core_dir: Path,
    content_type: str,
    active_packs: List[str],
    bundled_packs_dir: Optional[Path] = None,
    project_packs_dir: Optional[Path] = None,
    project_dir: Optional[Path] = None,
    user_packs_dir: Optional[Path] = None,
    user_dir: Optional[Path] = None,
    pack_roots: Optional[Iterable[Tuple[str, Path]]] = None,
    overlay_layers: Optional[Iterable[Tuple[str, Path]]] = None,
) -> List[Path]:
    """Build layered directory list: core → packs → overlay layers.

    Args:
        core_dir: Base directory for core modules (e.g., core/state/handlers/)
        content_type: Subdirectory name (e.g., "actions", "guards", "functions")
        bundled_packs_dir: Bundled packs directory (data/packs/) (legacy)
        user_packs_dir: Optional user packs directory (legacy)
        project_packs_dir: Project packs directory (legacy)
        user_dir: Optional user config directory (legacy)
        project_dir: Project config directory (legacy)
        pack_roots: Optional explicit pack roots in precedence order (preferred)
        overlay_layers: Optional explicit overlay layer roots in precedence order (preferred)
        active_packs: List of active pack names

    Returns:
        List of directories in layer order (core first, project last)
    """
    if pack_roots is not None and overlay_layers is not None:
        return [
            core_dir / content_type,
            *(
                Path(root) / pack / content_type
                for pack in active_packs
                for _kind, root in pack_roots
            ),
            *(Path(layer_root) / content_type for _lid, layer_root in overlay_layers),
        ]

    if bundled_packs_dir is None or project_packs_dir is None or project_dir is None:
        raise ValueError("build_layer_dirs requires either (pack_roots + overlay_layers) or legacy args.")

    return [
        core_dir / content_type,
        *(bundled_packs_dir / p / content_type for p in active_packs),
        *((user_packs_dir / p / content_type) for p in active_packs if user_packs_dir is not None),
        *(project_packs_dir / p / content_type for p in active_packs),
        *([user_dir / content_type] if user_dir is not None else []),
        project_dir / content_type,
    ]


def build_layer_dirs_from_resolver(
    core_dir: Path,
    content_type: str,
    resolver: "CompositionPathResolver",  # noqa: F821 - forward reference
    active_packs: List[str],
) -> List[Path]:
    """Build layered directory list using CompositionPathResolver.

    Convenience wrapper around build_layer_dirs for when a resolver is available.

    Args:
        core_dir: Base directory for core modules
        content_type: Subdirectory name (e.g., "actions", "guards")
        resolver: CompositionPathResolver instance
        active_packs: List of active pack names

    Returns:
        List of directories in layer order
    """
    return build_layer_dirs(
        core_dir=core_dir,
        content_type=content_type,
        active_packs=active_packs,
        pack_roots=[(r.kind, r.path) for r in resolver.pack_roots],
        overlay_layers=resolver.overlay_layers,
        bundled_packs_dir=resolver.bundled_packs_dir,
        user_packs_dir=getattr(resolver, "user_packs_dir", None),
        project_packs_dir=resolver.project_packs_dir,
        user_dir=getattr(resolver, "user_dir", None),
        project_dir=resolver.project_dir,
    )


def iter_python_files(
    dirs: Iterable[Path],
    exclude: Optional[Set[str]] = None,
) -> Iterable[Path]:
    """Yield all *.py files from existing directories in order.

    Args:
        dirs: Directories to search (in order)
        exclude: Set of filenames to exclude (default: {"__init__.py"})

    Yields:
        Paths to Python files
    """
    if exclude is None:
        exclude = {"__init__.py"}

    for d in dirs:
        if not d or not d.exists():
            continue
        for path in sorted(d.glob("*.py")):
            if path.is_file() and path.name not in exclude:
                yield path


def load_module_from_path(
    path: Path,
    namespace: str = "edison.dynamic",
) -> Optional[ModuleType]:
    """Dynamically load a Python module from file without adding to sys.modules.

    Args:
        path: Path to the .py file
        namespace: Module namespace prefix for the loaded module

    Returns:
        Loaded module or None on failure
    """
    module_name = f"{namespace}.{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            return module
    except Exception as e:
        logger.warning("Failed to load module %s: %s", path, e)
    return None


def register_callables_from_module(
    module: ModuleType,
    register_fn: Callable[[str, Callable[..., object]], None],
    exclude_prefixes: tuple[str, ...] = ("_",),
) -> int:
    """Register all public callables from a module.

    Args:
        module: Loaded Python module
        register_fn: Function to register handlers (e.g., registry.add)
        exclude_prefixes: Prefixes for names to skip (default: private "_")

    Returns:
        Number of callables registered
    """
    count = 0
    for name in dir(module):
        if any(name.startswith(p) for p in exclude_prefixes):
            continue
        obj = getattr(module, name)
        if callable(obj) and not isinstance(obj, type):
            register_fn(name, obj)
            count += 1
    return count


def load_and_register_modules(
    dirs: Iterable[Path],
    register_fn: Callable[[str, Callable[..., object]], None],
    namespace: str = "edison.dynamic",
    exclude_files: Optional[Set[str]] = None,
) -> int:
    """Load modules from directories and register their callables.

    Convenience function combining iter_python_files, load_module_from_path,
    and register_callables_from_module.

    Args:
        dirs: Directories to search (in layer order)
        register_fn: Function to register callables
        namespace: Module namespace prefix
        exclude_files: Filenames to exclude

    Returns:
        Total number of callables registered
    """
    total = 0
    for path in iter_python_files(dirs, exclude=exclude_files):
        module = load_module_from_path(path, namespace)
        if module:
            total += register_callables_from_module(module, register_fn)
    return total


__all__ = [
    "build_layer_dirs",
    "build_layer_dirs_from_resolver",
    "iter_python_files",
    "load_module_from_path",
    "register_callables_from_module",
    "load_and_register_modules",
]








