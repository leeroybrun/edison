"""Codex CLI platform adapter.

Handles:
- Codex-specific configurations
- Note: Codex only supports user-level prompts, not project-level

This is a minimal adapter as Codex has limited sync requirements.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class CodexAdapterError(RuntimeError):
    """Error in Codex adapter operations."""


class CodexAdapter(PlatformAdapter):
    """Platform adapter for Codex CLI.

    This adapter:
    - Provides minimal Codex-specific configuration
    - Note: Codex only supports user-level prompts, not project-level
    - Most work is done by composition system, adapter is minimal
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> None:
        """Initialize Codex adapter.

        Args:
            project_root: Project root directory.
            adapter_config: Adapter configuration from loader.
        """
        super().__init__(project_root=project_root, adapter_config=adapter_config)

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
        """Sync _generated/agents to .codex/prompts (or configured path).
        
        Uses sync configuration from CompositionConfig if available.
        """
        result: Dict[str, List[Path]] = {
            "agents": [],
        }
        
        # Use sync configuration if enabled
        if self.is_sync_enabled("agents"):
            dest_dir = self.get_sync_destination("agents")
            if dest_dir:
                dest_dir.mkdir(parents=True, exist_ok=True)
                result["agents"] = self.sync_agents_from_generated(dest_dir)
        else:
            # Default fallback
            codex_dir = self.project_root / ".codex" / "prompts"
            codex_dir.mkdir(parents=True, exist_ok=True)
            result["agents"] = self.sync_agents_from_generated(codex_dir)
        
        return result


__all__ = ["CodexAdapter", "CodexAdapterError"]
