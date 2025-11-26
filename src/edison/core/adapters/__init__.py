from __future__ import annotations

"""
Provider-agnostic prompt adapters.

This module provides two categories of adapters:

1. **PromptAdapter-based adapters** (thin views over `_generated`):
   Located in the `prompt/` subdirectory:
   - ClaudeAdapter: Projects into `.claude/`
   - ZenPromptAdapter: Projects into `.zen/conf/systemprompts/`
   - CursorPromptAdapter: Projects into `.cursor/`
   - CodexAdapter: Projects into `.codex/`

2. **Full-featured adapters** (composition + sync + validation):
   Located in the `sync/` subdirectory:
   - ClaudeSync: Full Claude Code integration with agent sync
   - ZenSync: Full Zen MCP integration with role composition
   - CursorSync: Full Cursor integration with .cursorrules management

Choose based on your use case:
- For rendering from `_generated` artifacts: Use PromptAdapter-based
- For full composition and sync: Use the full-featured sync adapters
"""

# ============================================================================
# Base and shared utilities
# ============================================================================
from .base import PromptAdapter  # noqa: F401
from ._config import ConfigMixin  # noqa: F401

# ============================================================================
# PromptAdapter-based adapters (thin views over _generated)
# ============================================================================
from .prompt.claude import ClaudeAdapter  # noqa: F401
from .prompt.zen import ZenPromptAdapter  # noqa: F401
from .prompt.codex import CodexAdapter  # noqa: F401
from .prompt.cursor import CursorPromptAdapter  # noqa: F401

# ============================================================================
# Full-featured adapters (composition + sync + validation)
# ============================================================================
from .sync.claude import (
    ClaudeSync,
    ClaudeAdapterError,
)
from .sync.cursor import CursorSync, AUTOGEN_BEGIN, AUTOGEN_END
from .sync.zen import ZenSync, WORKFLOW_HEADING

# ============================================================================
# Shared schema validation utilities (re-exported from core.schemas)
# ============================================================================
from ..schemas import (
    load_schema,
    validate_payload,
    validate_payload_safe,
    SchemaValidationError,
)

__all__ = [
    # Base and shared
    "PromptAdapter",
    "ConfigMixin",
    # PromptAdapter-based (thin)
    "ClaudeAdapter",
    "ZenPromptAdapter",
    "CursorPromptAdapter",
    "CodexAdapter",
    # Full-featured sync adapters
    "ClaudeSync",
    "ClaudeAdapterError",
    "CursorSync",
    "AUTOGEN_BEGIN",
    "AUTOGEN_END",
    "ZenSync",
    "WORKFLOW_HEADING",
    # Schema utilities
    "load_schema",
    "validate_payload",
    "validate_payload_safe",
    "SchemaValidationError",
]
