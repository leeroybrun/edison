"""Core pack utilities.

This package intentionally stays dependency-lite (no composition imports) to
avoid circular import issues.
"""

from .paths import PackRoot, get_pack_roots, iter_pack_dirs

__all__ = ["PackRoot", "get_pack_roots", "iter_pack_dirs"]

