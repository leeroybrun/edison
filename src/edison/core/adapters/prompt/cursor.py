from __future__ import annotations

"""
Cursor prompt adapter (thin).

Projects Edison `_generated` artifacts for Cursor IDE.
"""

from pathlib import Path
from typing import Dict, Optional

from ..base import PromptAdapter
from .._config import ConfigMixin


class CursorPromptAdapter(PromptAdapter, ConfigMixin):
    """Provider adapter for Cursor IDE (thin wrapper using PromptAdapter base)."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        # Initialize ConfigMixin cache
        self._cached_config: Optional[Dict] = None
        self.cursor_dir = self.repo_root / ".cursor"

    def generate_commands(self) -> Dict[str, Path]:
        """Generate slash commands for Cursor."""
        if not self.config.get("commands", {}).get("enabled"):
            return {}

        from ...composition.commands import CommandComposer

        composer = CommandComposer(self.config, self.repo_root)
        commands = composer.compose_for_platform("cursor", composer.load_definitions())

        return commands

    def write_outputs(self, output_root: Path) -> None:
        """Write prompts into output_root."""
        output_root.mkdir(parents=True, exist_ok=True)

        # Get adapter-specific config
        adapter_config = self.config.get("adapters", {}).get("cursor", {})

        # Write orchestrator
        if self.orchestrator_guide_path.exists():
            orchestrator_filename = adapter_config.get("orchestrator_filename", "cursor-orchestrator.txt")
            orchestrator_path = output_root / orchestrator_filename
            content = self.render_orchestrator(self.orchestrator_guide_path, self.orchestrator_manifest_path)
            orchestrator_path.write_text(content, encoding="utf-8")

        # Write agents
        agents_dirname = adapter_config.get("agents_dirname", "cursor-agents")
        agents_output_dir = output_root / agents_dirname
        agents_output_dir.mkdir(parents=True, exist_ok=True)

        for agent_name in self.list_agents():
            content = self.render_agent(agent_name)
            agent_path = agents_output_dir / f"{agent_name}.md"
            agent_path.write_text(content, encoding="utf-8")

        # Write validators
        validators_dirname = adapter_config.get("validators_dirname", "cursor-validators")
        validators_output_dir = output_root / validators_dirname
        validators_output_dir.mkdir(parents=True, exist_ok=True)

        for validator_name in self.list_validators():
            content = self.render_validator(validator_name)
            validator_path = validators_output_dir / f"{validator_name}.md"
            validator_path.write_text(content, encoding="utf-8")

        # Commands
        commands = self.generate_commands()
        if commands:
            print(f"✅ Generated {len(commands)} Cursor commands")

    # Config loading methods inherited from ConfigMixin

    def render_orchestrator(self, guide_path: Path, manifest_path: Path) -> str:
        """Render orchestrator prompt with workflow template."""
        if not guide_path.exists():
            raise FileNotFoundError(f"Orchestrator guide not found: {guide_path}")

        adapter_config = self.config.get("adapters", {}).get("cursor", {})
        workflow_template_path = adapter_config.get("workflow_template")

        content = guide_path.read_text(encoding="utf-8")

        # Add workflow marker
        workflow_section = "\n\n## Workflow\n\nThis orchestrator follows Edison workflow conventions."
        if workflow_template_path:
            template_path = self.repo_root / workflow_template_path
            if template_path.exists():
                workflow_content = template_path.read_text(encoding="utf-8")
                workflow_section = f"\n\n## Workflow\n\n{workflow_content}"

        return f"{content}{workflow_section}"

    def render_agent(self, agent_name: str) -> str:
        """Render agent prompt from _generated/agents/."""
        agent_path = self.agents_dir / f"{agent_name}.md"
        if not agent_path.exists():
            raise FileNotFoundError(f"Agent not found: {agent_path}")

        return agent_path.read_text(encoding="utf-8")

    def render_validator(self, validator_name: str) -> str:
        """Render validator prompt from _generated/validators/."""
        validator_path = self.validators_dir / f"{validator_name}.md"
        if not validator_path.exists():
            raise FileNotFoundError(f"Validator not found: {validator_path}")

        return validator_path.read_text(encoding="utf-8")


__all__ = ["CursorPromptAdapter"]
