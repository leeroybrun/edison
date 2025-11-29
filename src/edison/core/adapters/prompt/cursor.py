from __future__ import annotations

"""
Cursor prompt adapter.

Projects Edison prompts for Cursor IDE using composition.yaml configuration.
All paths are configurable - NO hardcoded paths.
"""

from pathlib import Path
from typing import Dict, Optional

from ..base import PromptAdapter
from .._config import ConfigMixin
from ...composition.output import OutputConfigLoader
from edison.core.utils.io import ensure_directory
from edison.core.config.domains import AdaptersConfig


class CursorPromptAdapter(PromptAdapter, ConfigMixin):
    """Provider adapter for Cursor IDE.

    Uses composition.yaml for all path configuration.
    """

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        self._cached_config: Optional[Dict] = None
        self._output_config = OutputConfigLoader(repo_root=self.repo_root)
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        self.cursor_dir = adapters_cfg.get_client_path("cursor")

    def generate_commands(self) -> Dict[str, Path]:
        """Generate slash commands for Cursor."""
        if not self.config.get("commands", {}).get("enabled"):
            return {}

        from ...composition.commands import CommandComposer

        composer = CommandComposer(self.config, self.repo_root)
        commands = composer.compose_for_platform("cursor", composer.load_definitions())

        return commands

    def write_outputs(self, output_root: Path) -> None:
        """Write prompts into output_root.
        
        Uses composition.yaml configuration for paths and settings.
        """
        # Check if cursor client is enabled
        client_cfg = self._output_config.get_client_config("cursor")
        if client_cfg is not None and not client_cfg.enabled:
            return
        
        ensure_directory(output_root)

        adapter_config = self.config.get("adapters", {}).get("cursor", {})

        # Write orchestrator constitution
        if self.orchestrator_constitution_path.exists():
            orchestrator_filename = adapter_config.get("orchestrator_filename", "cursor-orchestrator.txt")
            orchestrator_path = output_root / orchestrator_filename
            content = self._render_constitution()
            orchestrator_path.write_text(content, encoding="utf-8")

        # Write agents
        agents_dirname = adapter_config.get("agents_dirname", "cursor-agents")
        agents_output_dir = output_root / agents_dirname
        ensure_directory(agents_output_dir)

        for agent_name in self.list_agents():
            content = self.render_agent(agent_name)
            agent_path = agents_output_dir / f"{agent_name}.md"
            agent_path.write_text(content, encoding="utf-8")

        # Write validators
        validators_dirname = adapter_config.get("validators_dirname", "cursor-validators")
        validators_output_dir = output_root / validators_dirname
        ensure_directory(validators_output_dir)

        for validator_name in self.list_validators():
            content = self.render_validator(validator_name)
            validator_path = validators_output_dir / f"{validator_name}.md"
            validator_path.write_text(content, encoding="utf-8")

        # Commands
        commands = self.generate_commands()
        if commands:
            print(f"✅ Generated {len(commands)} Cursor commands")

    def _render_constitution(self) -> str:
        """Render orchestrator constitution with workflow template."""
        if not self.orchestrator_constitution_path.exists():
            raise FileNotFoundError(f"Orchestrator constitution not found: {self.orchestrator_constitution_path}")

        adapter_config = self.config.get("adapters", {}).get("cursor", {})
        workflow_template_path = adapter_config.get("workflow_template")

        content = self.orchestrator_constitution_path.read_text(encoding="utf-8")

        # Add workflow marker
        workflow_section = "\n\n## Workflow\n\nThis orchestrator follows Edison workflow conventions."
        if workflow_template_path:
            template_path = self.repo_root / workflow_template_path
            if template_path.exists():
                workflow_content = template_path.read_text(encoding="utf-8")
                workflow_section = f"\n\n## Workflow\n\n{workflow_content}"

        return f"{content}{workflow_section}"

    # Cursor uses default implementations from base class - no overrides needed


__all__ = ["CursorPromptAdapter"]
