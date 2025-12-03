"""Platform-specific adapters.

Platform adapters are platform-SPECIFIC implementations that extend PlatformAdapter.
Each adapter handles:
- Platform-specific sync logic
- Platform-specific formatting
- Platform-specific file layouts

Available platforms:
- ClaudeAdapter: Claude Code integration
- CursorAdapter: Cursor IDE integration
- ZenAdapter: Zen MCP integration
- CodexAdapter: Codex IDE integration
- CoderabbitAdapter: CodeRabbit integration
"""
from __future__ import annotations

from .claude import ClaudeAdapter, ClaudeAdapterError
from .cursor import CursorAdapter, CursorAdapterError
from .codex import CodexAdapter, CodexAdapterError
from .coderabbit import CoderabbitAdapter, CoderabbitAdapterError
from .zen import ZenAdapter, ZenAdapterError

__all__ = [
    "ClaudeAdapter",
    "ClaudeAdapterError",
    "CursorAdapter",
    "CursorAdapterError",
    "CodexAdapter",
    "CodexAdapterError",
    "CoderabbitAdapter",
    "CoderabbitAdapterError",
    "ZenAdapter",
    "ZenAdapterError",
]
