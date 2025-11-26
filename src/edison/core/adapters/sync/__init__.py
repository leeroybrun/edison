"""
Full-featured sync adapters.

These adapters provide complete IDE/client integration with synchronization,
configuration generation, and validation features.

- ClaudeSync: Full Claude Code integration
- CursorSync: Full Cursor IDE integration
- ZenSync: Full Zen MCP integration
"""

from .claude import ClaudeSync, ClaudeAdapterError
from .cursor import CursorSync, AUTOGEN_BEGIN, AUTOGEN_END
from .zen import ZenSync, WORKFLOW_HEADING

__all__ = [
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
