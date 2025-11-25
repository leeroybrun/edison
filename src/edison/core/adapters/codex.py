"""
Codex CLI adapter.

Projects Edison commands into user directory:
  - Commands: `~/.codex/prompts/edison-*.md`

Note: Codex only supports user-level prompts, not project-level.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .base import PromptAdapter


class CodexAdapter(PromptAdapter):
    """Provider adapter for Codex CLI."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        self._cached_config: Optional[Dict] = None

    def generate_commands(self) -> Dict[str, Path]:
        """Generate prompts for Codex (user directory)."""
        if not self.config.get("commands", {}).get("enabled"):
            return {}

        from ..composition.commands import CommandComposer

        composer = CommandComposer(self.config, self.repo_root)
        commands = composer.compose_for_platform("codex", composer.load_definitions())

        # Warn about user scope
        if commands:
            print(f"⚠️  Codex prompts are global (user-level), not project-specific")
            print(f"    Location: ~/.codex/prompts/")

        return commands

    def write_outputs(self, output_root: Path) -> None:
        """Generate Codex prompts (user directory)."""
        # Commands
        commands = self.generate_commands()
        if commands:
            print(f"✅ Generated {len(commands)} Codex prompts")

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
        return ""

    def render_agent(self, agent_name: str) -> str:
        return ""

    def render_validator(self, validator_name: str) -> str:
        return ""


__all__ = ["CodexAdapter"]
