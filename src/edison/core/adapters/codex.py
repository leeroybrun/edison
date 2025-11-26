"""
Backward compatibility shim for codex adapter imports.

DEPRECATED: Import from edison.core.adapters instead:
  - from edison.core.adapters import CodexAdapter
"""

from .prompt.codex import CodexAdapter

__all__ = ["CodexAdapter"]
