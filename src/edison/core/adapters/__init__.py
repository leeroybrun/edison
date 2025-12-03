from __future__ import annotations

"""
Platform adapters for Edison integrations.

All platform adapters now inherit from PlatformAdapter and are located in
the platforms/ subdirectory. This provides a unified architecture for:
- Claude Code (.claude/)
- Cursor (.cursor/, .cursorrules)
- Zen MCP (.zen/)
- CodeRabbit (.coderabbit.yaml)
- Codex (.codex/)
"""

# ============================================================================
# Base and shared utilities
# ============================================================================
from .base import PlatformAdapter  # noqa: F401

# ============================================================================
# Platform adapters (unified architecture)
# ============================================================================
from .platforms.claude import ClaudeAdapter  # noqa: F401
from .platforms.zen import ZenAdapter, WORKFLOW_HEADING  # noqa: F401
from .platforms.codex import CodexAdapter  # noqa: F401
from .platforms.cursor import CursorAdapter  # noqa: F401
from .platforms.coderabbit import CoderabbitAdapter  # noqa: F401

# Backward compatibility alias
CodeRabbitAdapter = CoderabbitAdapter

# Backward compatibility aliases
ClaudeSync = ClaudeAdapter
CursorSync = CursorAdapter
ZenSync = ZenAdapter

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
    # Base
    "PlatformAdapter",
    # Platform adapters
    "ClaudeAdapter",
    "ZenAdapter",
    "CursorAdapter",
    "CodexAdapter",
    "CodeRabbitAdapter",
    # Backward compatibility
    "ClaudeSync",
    "CursorSync",
    "ZenSync",
    "WORKFLOW_HEADING",
    # Schema utilities
    "load_schema",
    "validate_payload",
    "validate_payload_safe",
    "SchemaValidationError",
]
