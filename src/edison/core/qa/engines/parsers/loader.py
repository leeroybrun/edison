"""Parser loader for the validator engine system.

Loads parsers from multiple layers following Edison's extensible handler pattern:
1. Core parsers: core/qa/engines/parsers/ (built-in with Edison)
2. Bundled pack parsers: data/packs/<pack>/parsers/
3. Project pack parsers: .edison/packs/<pack>/parsers/
4. Project parsers: .edison/parsers/

Later layers override earlier ones, allowing customization at any level.
"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterable

from .base import ParseResult

logger = logging.getLogger(__name__)


# Global parser registry
_PARSERS: dict[str, Callable[[str], ParseResult]] = {}


def get_parser(name: str) -> Callable[[str], ParseResult] | None:
    """Get a registered parser by name.

    Args:
        name: Parser name (file stem, e.g., "codex", "gemini")

    Returns:
        Parser function or None if not found
    """
    return _PARSERS.get(name)


def register_parser(name: str, parser_fn: Callable[[str], ParseResult]) -> None:
    """Register a parser function.

    Args:
        name: Parser name (used as identifier in config)
        parser_fn: Parser function matching ParserProtocol
    """
    _PARSERS[name] = parser_fn
    logger.debug(f"Registered parser: {name}")


def list_parsers() -> list[str]:
    """List all registered parser names.

    Returns:
        List of parser names
    """
    return list(_PARSERS.keys())


def _iter_parser_files(dirs: Iterable[Path]) -> Iterable[Path]:
    """Yield all .py files from existing directories.

    Excludes __init__.py, base.py, and loader.py (infrastructure files).

    Args:
        dirs: Directories to search

    Yields:
        Paths to parser files
    """
    excluded = {"__init__.py", "base.py", "loader.py"}

    for dir_path in dirs:
        if not dir_path.exists() or not dir_path.is_dir():
            continue

        for path in sorted(dir_path.glob("*.py")):
            if path.name not in excluded:
                yield path


def _load_module(path: Path) -> ModuleType | None:
    """Dynamically load a Python module from path.

    Args:
        path: Path to .py file

    Returns:
        Loaded module or None on failure
    """
    try:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            logger.warning(f"Failed to load spec for {path}")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    except Exception as e:
        logger.warning(f"Failed to load parser module {path}: {e}")
        return None


def load_parsers(project_root: Path | None = None, active_packs: list[str] | None = None) -> None:
    """Load and register parsers from all layers.

    Follows the Edison extensible handler pattern:
    - Core parsers are loaded first
    - Pack parsers can extend/override
    - Project parsers have final override

    Args:
        project_root: Project root path (for pack/project parsers)
        active_packs: List of active pack names
    """
    if active_packs is None:
        active_packs = []

    # Build list of parser directories in order (later overrides earlier)
    dirs: list[Path] = []

    # 1. Core parsers (this directory)
    core_parsers = Path(__file__).parent
    dirs.append(core_parsers)

    # 2-4. Pack and project parsers (if project_root provided)
    if project_root:
        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(project_root)

        # 2. Bundled pack parsers
        for pack in active_packs:
            pack_dir = resolver.bundled_packs_dir / pack / "parsers"
            dirs.append(pack_dir)

        # 3. Project pack parsers
        for pack in active_packs:
            pack_dir = resolver.project_packs_dir / pack / "parsers"
            dirs.append(pack_dir)

        # 4. Project parsers
        project_parsers = resolver.project_dir / "parsers"
        dirs.append(project_parsers)

    # Load parsers from all directories
    for path in _iter_parser_files(dirs):
        module = _load_module(path)
        if module and hasattr(module, "parse"):
            # Parser ID = file stem (codex.py → "codex")
            parser_id = path.stem
            register_parser(parser_id, module.parse)


def ensure_parsers_loaded(project_root: Path | None = None, active_packs: list[str] | None = None) -> None:
    """Ensure parsers are loaded (idempotent).

    Safe to call multiple times - only loads parsers once.

    Args:
        project_root: Project root path
        active_packs: List of active pack names
    """
    if not _PARSERS:
        load_parsers(project_root, active_packs)


__all__ = [
    "ensure_parsers_loaded",
    "get_parser",
    "list_parsers",
    "load_parsers",
    "register_parser",
]

