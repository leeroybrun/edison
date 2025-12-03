"""Codex CLI platform adapter.

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
        """Sync _generated/agents to ~/.codex/prompts (or configured path)."""
        # Allow overrides via output_config; default to project-local to stay sandbox-safe
        cfg = self.output_config.get_sync_config("codex")
        if cfg and cfg.enabled and cfg.agents_path:
            codex_dir = self.output_config._resolve_path(cfg.agents_path)
        else:
            codex_dir = self.project_root / ".codex" / "prompts"
        codex_dir.mkdir(parents=True, exist_ok=True)

        written = self.sync_agents_from_generated(codex_dir)
        return {"agents": written}


__all__ = ["CodexAdapter", "CodexAdapterError"]
