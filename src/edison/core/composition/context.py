"""Unified composition context.

Provides a single CompositionContext dataclass used throughout the composition system:
- Strategies (MarkdownCompositionStrategy)
- Transformers (conditionals, loops, etc.)
- Generators (rosters, state machine)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CompositionContext:
    """Context for all composition operations.

    Provides shared state for:
    - Strategies composing layered content
    - Transformers processing templates
    - Generators creating documents

    Attributes:
        active_packs: List of active pack names
        config: Configuration dictionary
        project_root: Optional project root path
        source_dir: Optional source directory for resolving includes
        context_vars: Custom template variables for {{var}} substitution and {{#each}} loops.
            These flow through to TemplateEngine and are merged with defaults
            (source_layers, timestamp). Values can be strings for simple substitution
            or lists/dicts for loop expansion.
    """

    active_packs: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    project_root: Optional[Path] = None
    source_dir: Optional[Path] = None
    context_vars: Dict[str, Any] = field(default_factory=dict)

    def get_config(self, path: str) -> Any:
        """Get config value by dot-separated path.

        Args:
            path: Dot-separated path like 'features.auth.enabled'

        Returns:
            The config value or None if not found
        """
        parts = path.split(".")
        current: Any = self.config
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def has_pack(self, pack_name: str) -> bool:
        """Check if a pack is active.

        Args:
            pack_name: Name of the pack to check

        Returns:
            True if the pack is in active_packs
        """
        return pack_name in self.active_packs


__all__ = ["CompositionContext"]
