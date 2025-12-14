"""Include-related utilities for the composition engine.

NOTE:
- Template syntax parsing lives in `edison.core.composition.transformers.includes`.
- This package provides *where to load include targets from* (the composed view).
"""

from .provider import ComposedIncludeProvider, merge_extends_preserve_sections
from .resolution import ComposeError, resolve_includes

__all__ = ["ComposedIncludeProvider", "merge_extends_preserve_sections", "ComposeError", "resolve_includes"]

