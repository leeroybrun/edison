"""
Full-featured sync adapters.

These adapters provide complete IDE/client integration with synchronization,
configuration generation, and validation features.

- ClaudeSync: Full Claude Code integration (formerly ClaudeCodeAdapter)
- CursorSync: Full Cursor IDE integration (formerly CursorAdapter)
- ZenSync: Full Zen MCP integration (formerly ZenAdapter)
"""

from .claude import ClaudeSync, ClaudeAdapterError, EdisonAgentSections
from .cursor import CursorSync, AUTOGEN_BEGIN, AUTOGEN_END
from .zen import ZenSync, WORKFLOW_HEADING

__all__ = [
    # Claude
    "ClaudeSync",
    "ClaudeAdapterError",
    "EdisonAgentSections",
    # Cursor
    "CursorSync",
    "AUTOGEN_BEGIN",
    "AUTOGEN_END",
    # Zen
    "ZenSync",
    "WORKFLOW_HEADING",
]
