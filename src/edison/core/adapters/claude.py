"""
Backward compatibility shim for claude adapter imports.

DEPRECATED: Import from edison.core.adapters instead:
  - from edison.core.adapters import ClaudeAdapter  # Thin adapter
  - from edison.core.adapters import ClaudeSync  # Full-featured (formerly ClaudeCodeAdapter)
  - from edison.core.adapters import ClaudeCodeAdapter  # Backward compat alias for ClaudeSync
"""

from .prompt.claude import ClaudeAdapter
from .sync.claude import ClaudeSync, ClaudeAdapterError, EdisonAgentSections

# Backward compatibility alias
ClaudeCodeAdapter = ClaudeSync

__all__ = [
    "ClaudeAdapter",
    "ClaudeSync",
    "ClaudeCodeAdapter",
    "ClaudeAdapterError",
    "EdisonAgentSections",
]
