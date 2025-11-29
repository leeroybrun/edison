"""
Full-featured sync adapters.

These adapters provide complete IDE/client integration with synchronization,
configuration generation, and validation features.

- SyncAdapter: Abstract base class for all sync adapters
- ClaudeSync: Full Claude Code integration
- CursorSync: Full Cursor IDE integration
- ZenSync: Full Zen MCP integration
"""

from .base import SyncAdapter
from .claude import ClaudeSync, ClaudeAdapterError
from .cursor import CursorSync, AUTOGEN_BEGIN, AUTOGEN_END
from .zen import ZenSync, WORKFLOW_HEADING

__all__ = [
    # Base
    "SyncAdapter",
    # Claude
    "ClaudeSync",
    "ClaudeAdapterError",
    # Cursor
    "CursorSync",
    "AUTOGEN_BEGIN",
    "AUTOGEN_END",
    # Zen
    "ZenSync",
    "WORKFLOW_HEADING",
]
