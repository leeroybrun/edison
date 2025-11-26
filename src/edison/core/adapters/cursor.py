"""
Backward compatibility shim for cursor adapter imports.

DEPRECATED: Import from edison.core.adapters instead:
  - from edison.core.adapters import CursorPromptAdapter  # Thin adapter
  - from edison.core.adapters import CursorSync  # Full-featured (formerly CursorAdapter)
  - from edison.core.adapters import CursorAdapter  # Backward compat alias for CursorSync
"""

from .prompt.cursor import CursorPromptAdapter
from .sync.cursor import CursorSync, AUTOGEN_BEGIN, AUTOGEN_END

# Backward compatibility alias
CursorAdapter = CursorSync

__all__ = [
    "CursorPromptAdapter",
    "CursorSync",
    "CursorAdapter",
    "AUTOGEN_BEGIN",
    "AUTOGEN_END",
]
