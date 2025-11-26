"""
Backward compatibility shim for zen adapter imports.

DEPRECATED: Import from edison.core.adapters instead:
  - from edison.core.adapters import ZenPromptAdapter  # Thin adapter
  - from edison.core.adapters import ZenSync  # Full-featured (formerly ZenAdapter)
  - from edison.core.adapters import ZenAdapter  # Backward compat alias for ZenSync
"""

from .prompt.zen import ZenPromptAdapter, WORKFLOW_HEADING
from .sync.zen import ZenSync

# Backward compatibility alias
ZenAdapter = ZenSync

__all__ = [
    "ZenPromptAdapter",
    "ZenSync",
    "ZenAdapter",
    "WORKFLOW_HEADING",
]
