"""
Cursor IDE adapter.

Projects Edison `_generated` artifacts into `.cursor/` directory:
  - Commands: `.cursor/commands/*.md`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .base import PromptAdapter


class CursorAdapter(PromptAdapter):
    """Provider adapter for Cursor IDE."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        self._cached_config: Optional[Dict] = None
        self.cursor_dir = self.repo_root / ".cursor"

    def generate_commands(self) -> Dict[str, Path]:
        """Generate slash commands for Cursor."""
        if not self.config.get("commands", {}).get("enabled"):
            return {}

        from ..composition.commands import CommandComposer

        composer = CommandComposer(self.config, self.repo_root)
        commands = composer.compose_for_platform("cursor", composer.load_definitions())

        return commands

    def write_outputs(self, output_root: Path) -> None:
        """Write commands into `.cursor/`."""
        output_root.mkdir(parents=True, exist_ok=True)

        # Commands
        commands = self.generate_commands()
        if commands:
            print(f"✅ Generated {len(commands)} Cursor commands")

    def _load_config(self) -> Dict:
        """Load Edison config."""
        if self._cached_config is not None:
            return self._cached_config

        from ..config import ConfigManager

        try:
            mgr = ConfigManager(self.repo_root)
            self._cached_config = mgr.load_config(validate=False)
        except Exception:
            self._cached_config = {}
        return self._cached_config

    @property
    def config(self) -> Dict:
        """Lazy load config."""
        return self._load_config()

    # Stub methods for PromptAdapter interface
    def render_orchestrator(self, guide_path: Path, manifest_path: Path) -> str:
        return ""  # Cursor doesn't use orchestrator

    def render_agent(self, agent_name: str) -> str:
        return ""  # Cursor doesn't use agents

    def render_validator(self, validator_name: str) -> str:
        return ""  # Cursor doesn't use validators

class CursorPromptAdapter(CursorAdapter):
    """Backward-compatible alias for legacy imports."""


__all__ = ["CursorAdapter", "CursorPromptAdapter"]
