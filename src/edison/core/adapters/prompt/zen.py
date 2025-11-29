from __future__ import annotations

"""Zen MCP prompt adapter.

Renders Edison `_generated` artifacts for Zen MCP consumption.
All output paths are configurable via composition.yaml - NO hardcoded paths.

This adapter does NOT do composition - it reads pre-composed files
from the unified composition engine output.

Output location: Configurable via composition.yaml (default: .zen/conf/systemprompts/)
"""

from pathlib import Path
from typing import List, Optional

from edison.core.utils.io import ensure_directory
from ...composition.output import OutputConfigLoader
from ..base import PromptAdapter
from edison.core.config.domains import AdaptersConfig


WORKFLOW_HEADING = "## Edison Workflow Loop"


class ZenPromptAdapter(PromptAdapter):
    """Adapter for generating Zen MCP system prompts from _generated/."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root=repo_root)
        self.project_config_dir_name = self.generated_root.parent.name
        self._config = OutputConfigLoader(repo_root=self.repo_root)
        self._adapters_cfg = AdaptersConfig(repo_root=self.repo_root)

    def _workflow_loop_block(self) -> str:
        """Return shared workflow loop block for all Zen prompts."""
        template = self._adapters_cfg.get_template_path("zen", "workflow-loop.txt")
        if template.exists():
            return template.read_text(encoding="utf-8").strip()
        raise FileNotFoundError(
            f"Zen workflow template not found: {template}. "
            "This template is required for Zen prompt generation."
        )

    def _post_process_agent(self, agent_name: str, content: str) -> str:
        """Format agent content for Zen MCP.

        Args:
            agent_name: Name of the agent.
            content: Raw agent content from file.

        Returns:
            Zen-formatted agent prompt.
        """
        workflow_block = self._workflow_loop_block()

        lines: List[str] = [
            "=== Edison / Zen MCP Prompt ===",
            f"Role: {agent_name}",
            "",
            f"Constitution: {self.project_config_dir_name}/_generated/constitutions/AGENTS.md",
            "",
            content.strip(),
            "",
            workflow_block,
        ]

        return "\n".join(lines).rstrip() + "\n"

    def _post_process_validator(self, validator_name: str, content: str) -> str:
        """Format validator content for Zen MCP.

        Args:
            validator_name: Name of the validator.
            content: Raw validator content from file.

        Returns:
            Zen-formatted validator prompt.
        """
        workflow_block = self._workflow_loop_block()

        lines: List[str] = [
            "=== Edison / Zen MCP Validator Prompt ===",
            f"Validator: {validator_name}",
            "",
            f"Constitution: {self.project_config_dir_name}/_generated/constitutions/VALIDATORS.md",
            "",
            content.strip(),
            "",
            workflow_block,
        ]

        return "\n".join(lines).rstrip() + "\n"

    def write_outputs(self, output_root: Path) -> None:
        """Write role-specific prompts into the Zen MCP prompt directory.
        
        Uses composition.yaml configuration for output paths when available.
        
        Args:
            output_root: Directory to write prompt files to (can be overridden by config).
        """
        # Check if zen client is enabled
        zen_cfg = self._config.get_client_config("zen")
        if zen_cfg is not None and not zen_cfg.enabled:
            return
        
        # Use config-based sync path if available
        sync_cfg = self._config.get_sync_config("zen")
        if sync_cfg and sync_cfg.enabled and sync_cfg.prompts_path:
            output_dir = self._config._resolve_path(sync_cfg.prompts_path)
            filename_pattern = sync_cfg.prompts_filename_pattern or "{name}.txt"
        else:
            output_dir = output_root
            filename_pattern = "{name}.txt"
        
        ensure_directory(output_dir)
        
        # Write client file
        try:
            client_content = self.render_client("zen")
            (output_dir / "zen.txt").write_text(client_content, encoding="utf-8")
        except FileNotFoundError:
            pass
        
        # Write agent prompts
        for agent_name in self.list_agents():
            try:
                text = self.render_agent(agent_name)
                filename = filename_pattern.format(name=agent_name)
                (output_dir / filename).write_text(text, encoding="utf-8")
            except FileNotFoundError:
                continue
        
        # Write validator prompts
        for validator_name in self.list_validators():
            try:
                text = self.render_validator(validator_name)
                filename = filename_pattern.format(name=validator_name)
                (output_dir / filename).write_text(text, encoding="utf-8")
            except FileNotFoundError:
                continue


__all__ = ["ZenPromptAdapter", "WORKFLOW_HEADING"]
