"""Parser loader for the validator engine system.

Loads parsers from multiple layers following Edison's extensible handler pattern:
1. Core parsers: core/qa/engines/parsers/ (built-in with Edison)
2. Bundled pack parsers: data/packs/<pack>/parsers/
3. User pack parsers: ~/<user-config-dir>/packs/<pack>/parsers/
4. Project pack parsers: <project-config-dir>/packs/<pack>/parsers/
5. User parsers: ~/<user-config-dir>/parsers/
6. Project parsers: <project-config-dir>/parsers/

Later layers override earlier ones, allowing customization at any level.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List

from edison.core.utils.loader import (
    iter_python_files,
    load_module_from_path,
)
from .base import ParseResult

logger = logging.getLogger(__name__)


# Global parser registry
_PARSERS: dict[str, Callable[[str], ParseResult]] = {}

# Core parsers directory (this directory)
_CORE_PARSERS_DIR = Path(__file__).parent

# Files to exclude when loading parsers (infrastructure files)
_EXCLUDED_FILES = {"__init__.py", "base.py", "loader.py"}


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
    dirs: List[Path] = []

    # 1. Core parsers (this directory)
    dirs.append(_CORE_PARSERS_DIR)

    # 2-4. Pack and project parsers (if project_root provided)
    if project_root:
        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(project_root)

        # 2. Bundled pack parsers
        for pack in active_packs:
            pack_dir = resolver.bundled_packs_dir / pack / "parsers"
            dirs.append(pack_dir)

        # 3. User pack parsers
        for pack in active_packs:
            pack_dir = resolver.user_packs_dir / pack / "parsers"
            dirs.append(pack_dir)

        # 4. Project pack parsers
        for pack in active_packs:
            pack_dir = resolver.project_packs_dir / pack / "parsers"
            dirs.append(pack_dir)

        # 5. User parsers
        dirs.append(resolver.user_dir / "parsers")

        # 6. Project parsers
        project_parsers = resolver.project_dir / "parsers"
        dirs.append(project_parsers)

    # Load parsers from all directories using common utility
    for path in iter_python_files(dirs, exclude=_EXCLUDED_FILES):
        # Load under the real package namespace so parser modules can use
        # relative imports like `from .base import ParseResult`.
        module = load_module_from_path(path, "edison.core.qa.engines.parsers")
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
