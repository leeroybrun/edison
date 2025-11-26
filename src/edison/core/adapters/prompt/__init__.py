"""
Thin prompt adapters.

These adapters are lightweight wrappers that project Edison `_generated`
artifacts into provider-specific formats without full synchronization features.

- ClaudeAdapter: Projects into `.claude/`
- CursorPromptAdapter: Projects for Cursor IDE
- ZenPromptAdapter: Projects into `.zen/conf/systemprompts/`
- CodexAdapter: Projects into user `~/.codex/prompts/`
"""

from .claude import ClaudeAdapter
from .cursor import CursorPromptAdapter
from .zen import ZenPromptAdapter
from .codex import CodexAdapter

__all__ = [
    "ClaudeAdapter",
    "CursorPromptAdapter",
    "ZenPromptAdapter",
    "CodexAdapter",
]
