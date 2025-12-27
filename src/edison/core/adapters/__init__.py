from __future__ import annotations

"""
Platform adapters for Edison integrations.

All platform adapters now inherit from PlatformAdapter and are located in
the platforms/ subdirectory. This provides a unified architecture for:
- Claude Code (.claude/)
- Cursor (.cursor/)
- Pal MCP (.pal/)
- CodeRabbit (.coderabbit.yaml)
- Codex (.codex/)
"""

# ============================================================================
# Base and shared utilities
# ============================================================================
from .base import PlatformAdapter  # noqa: F401
from .loader import AdapterLoader  # noqa: F401

# ============================================================================
# Platform adapters (unified architecture)
# ============================================================================
from .platforms.claude import ClaudeAdapter  # noqa: F401
from .platforms.managed_files import ManagedFilesAdapter  # noqa: F401
from .platforms.pal import PalAdapter  # noqa: F401
from .platforms.codex import CodexAdapter  # noqa: F401
from .platforms.cursor import CursorAdapter  # noqa: F401
from .platforms.coderabbit import CoderabbitAdapter  # noqa: F401

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
    # Loader
    "AdapterLoader",
    # Platform adapters
    "ClaudeAdapter",
    "ManagedFilesAdapter",
    "PalAdapter",
    "CursorAdapter",
    "CodexAdapter",
    "CoderabbitAdapter",
    # Schema utilities
    "load_schema",
    "validate_payload",
    "validate_payload_safe",
    "SchemaValidationError",
]
