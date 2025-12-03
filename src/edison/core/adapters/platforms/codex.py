"""Codex CLI platform adapter.

This adapter is based on:
- adapters/prompt/codex.py (CodexAdapter)

Handles:
- Codex-specific configurations
- Note: Codex only supports user-level prompts, not project-level

This is a minimal adapter as Codex has limited sync requirements.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.adapters.base import PlatformAdapter


class CodexAdapterError(RuntimeError):
    """Error in Codex adapter operations."""


class CodexAdapter(PlatformAdapter):
    """Platform adapter for Codex CLI.

    This adapter:
    - Provides minimal Codex-specific configuration
    - Note: Codex only supports user-level prompts, not project-level
    - Most work is done by composition system, adapter is minimal
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize Codex adapter.

        Args:
            project_root: Project root directory.
        """
        super().__init__(project_root=project_root)

    # =========================================================================
    # Platform Properties
    # =========================================================================

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "codex"

    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization workflow.

        Codex has minimal sync requirements as it uses user-level prompts.

        Returns:
            Empty dictionary (Codex doesn't sync project-level files).
        """
        # Codex only supports user-level prompts, not project-level sync
        # All composition happens via the main composition engine
        return {}


__all__ = ["CodexAdapter", "CodexAdapterError"]
