from __future__ import annotations

"""
Provider-agnostic prompt adapters.

These adapters project Edison `_generated` artifacts (under
`<project_config_dir>/_generated/`) into provider-specific layouts such as:

  - `.claude/` (Claude Code)
  - `.zen/conf/systemprompts/**` (Zen MCP)
  - `.cursor/**` (Cursor)

Composition logic lives in the core engine; adapters are thin views over
the `_generated` tree and must not re-run include or pack resolution.
"""

from .base import PromptAdapter  # noqa: F401
from .claude import ClaudeAdapter  # noqa: F401
from .zen import ZenPromptAdapter  # noqa: F401
from .codex import CodexAdapter  # noqa: F401
from .cursor import CursorAdapter  # noqa: F401

__all__ = [
    "PromptAdapter",
    "ClaudeAdapter",
    "ZenPromptAdapter",
    "CodexAdapter",
    "CursorAdapter",
]
