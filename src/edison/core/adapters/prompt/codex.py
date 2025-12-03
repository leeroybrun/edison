"""Codex CLI adapter.

Projects Edison prompts into user directory using composition.yaml configuration.
All paths are configurable - NO hardcoded paths.

Note: Codex only supports user-level prompts, not project-level.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from ..base import PromptAdapter
from ...composition.output import OutputConfigLoader
from ...composition.output.writer import CompositionFileWriter
from edison.core.utils.io import ensure_directory


class CodexAdapter(PromptAdapter):
    """Provider adapter for Codex CLI.

    Inherits from PromptAdapter which provides:
    - config property via ConfigMixin
    - active_packs property via ConfigMixin

    Uses composition.yaml for all path configuration.
    """

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        self._output_config = OutputConfigLoader(repo_root=self.repo_root)
        self._writer: Optional[CompositionFileWriter] = None

    @property
    def writer(self) -> CompositionFileWriter:
        """Lazy-initialized file writer for composition outputs."""
        if self._writer is None:
            self._writer = CompositionFileWriter(base_dir=self.repo_root)
        return self._writer

    def generate_commands(self) -> Dict[str, Path]:
        """Generate prompts for Codex (user directory)."""
        if not self.config.get("commands", {}).get("enabled"):
            return {}

        from ...composition.commands import CommandComposer

        composer = CommandComposer(self.config, self.repo_root)
        commands = composer.compose_for_platform("codex", composer.load_definitions())

        if commands:
            print("⚠️  Codex prompts are global (user-level), not project-specific")
            print("    Location: ~/.codex/prompts/")

        return commands

    def write_outputs(self, output_root: Path) -> None:
        """Generate Codex prompts to output_root.

        Uses composition.yaml configuration for paths and settings.
        """
        # Check if codex client is enabled
        client_cfg = self._output_config.get_client_config("codex")
        if client_cfg is not None and not client_cfg.enabled:
            return

        ensure_directory(output_root)

        adapter_config = self.config.get("adapters", {}).get("codex", {})

        # Write orchestrator constitution
        if self.orchestrator_constitution_path.exists():
            orchestrator_filename = adapter_config.get("orchestrator_filename", "SYS_PROMPT.md")
            orchestrator_path = output_root / orchestrator_filename
            content = self._render_constitution()
            self.writer.write_text(orchestrator_path, content)

        # Write agents
        agents_dirname = adapter_config.get("agents_dirname", "agent-prompts")
        agents_output_dir = output_root / agents_dirname
        ensure_directory(agents_output_dir)

        for agent_name in self.list_agents():
            content = self.render_agent(agent_name)
            agent_path = agents_output_dir / f"{agent_name}.md"
            self.writer.write_text(agent_path, content)

        # Write validators
        validators_dirname = adapter_config.get("validators_dirname", "validator-prompts")
        validators_output_dir = output_root / validators_dirname
        ensure_directory(validators_output_dir)

        for validator_name in self.list_validators():
            content = self.render_validator(validator_name)
            validator_path = validators_output_dir / f"{validator_name}.md"
            self.writer.write_text(validator_path, content)

        # Commands
        commands = self.generate_commands()
        if commands:
            print(f"✅ Generated {len(commands)} Codex prompts")

    def _render_constitution(self) -> str:
        """Render orchestrator constitution for Codex."""
        if not self.orchestrator_constitution_path.exists():
            raise FileNotFoundError(f"Orchestrator constitution not found: {self.orchestrator_constitution_path}")

        adapter_config = self.config.get("adapters", {}).get("codex", {})
        header = adapter_config.get("header", "# Codex System Prompt")

        content = self.orchestrator_constitution_path.read_text(encoding="utf-8")
        return f"{header}\n\n{content}"

    # Codex uses default implementations from base class - no overrides needed


__all__ = ["CodexAdapter"]
