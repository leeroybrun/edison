"""Shared helper for compose subcommands that use adapter components.

Some compose subcommands (commands/hooks/settings) operate via adapter components
that require an AdapterContext. This module provides a minimal PlatformAdapter
to construct that context without invoking any platform-specific sync logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.adapters.base import PlatformAdapter
from edison.core.adapters.components.base import AdapterContext


class _ComposeCLIAdapter(PlatformAdapter):
    """Minimal adapter used only to build AdapterContext for compose CLIs."""

    def __init__(self, *, project_root: Path, config_override: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(project_root=project_root)
        if config_override:
            # Tests/CLIs may pass an override; merge it on top of loaded config.
            self.config = self.cfg_mgr.deep_merge(self.config, config_override)

    @property
    def platform_name(self) -> str:
        return "compose-cli"

    def sync_all(self) -> Dict[str, Any]:
        return {}


def build_compose_context(*, repo_root: Path, config_override: Optional[Dict[str, Any]] = None) -> AdapterContext:
    """Create an AdapterContext suitable for adapter components in compose CLIs."""
    adapter = _ComposeCLIAdapter(project_root=repo_root, config_override=config_override)
    return adapter.context


__all__ = ["build_compose_context"]

