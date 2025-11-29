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

    # Claude uses default implementations from base class - no overrides needed

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
