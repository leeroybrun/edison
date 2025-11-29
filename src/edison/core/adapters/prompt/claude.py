from __future__ import annotations

"""Claude prompt adapter.

Renders Edison `_generated` artifacts for Claude Code consumption.
This adapter does NOT do composition - it reads pre-composed files
from the unified composition engine output.

For syncing to .claude/ directory, use ClaudeSync from adapters/sync/claude.py.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..base import PromptAdapter
from edison.core.utils.io import ensure_directory
from edison.core.config.domains import AdaptersConfig


class ClaudeAdapter(PromptAdapter):
    """Adapter for rendering Claude Code prompts from _generated/."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        self.claude_dir = adapters_cfg.get_client_path("claude")

    def render_client(self) -> str:
        """Render Claude client file from _generated/clients/claude.md.
        
        Returns:
            Content of the Claude client configuration.
        """
        source = self.clients_dir / "claude.md"
        if not source.exists():
            raise FileNotFoundError(f"Client file not found: {source}")
        return source.read_text(encoding="utf-8")

    def render_agent(self, agent_name: str) -> str:
        """Render agent from _generated/agents/.
        
        Args:
            agent_name: Name of the agent to render.
            
        Returns:
            Agent content.
        """
        source = self.agents_dir / f"{agent_name}.md"
        if not source.exists():
            raise FileNotFoundError(f"Agent not found: {source}")
        return source.read_text(encoding="utf-8")

    def render_validator(self, validator_name: str) -> str:
        """Render validator from _generated/validators/.
        
        Args:
            validator_name: Name of the validator to render.
            
        Returns:
            Validator content.
        """
        source = self.validators_dir / f"{validator_name}.md"
        if not source.exists():
            raise FileNotFoundError(f"Validator not found: {source}")
        return source.read_text(encoding="utf-8")

    def write_outputs(self, output_root: Path) -> None:
        """Write all outputs to Claude Code layout.
        
        Delegates to ClaudeSync for proper formatting and directory structure.
        
        Args:
            output_root: Output directory (typically .claude/)
        """
        ensure_directory(output_root)
        
        # Delegate to ClaudeSync for proper Claude Code layout
        from ..sync.claude import ClaudeSync
        sync = ClaudeSync(repo_root=self.repo_root)
        sync.sync_all()


__all__ = ["ClaudeAdapter"]
