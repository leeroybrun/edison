"""Claude Code platform adapter.

Handles:
- Syncing Edison-composed outputs to Claude Code layout
- Adding Claude-specific frontmatter to agents
- Managing .claude/ directory structure
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.adapters.base import PlatformAdapter
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.io import ensure_directory
from edison.core.adapters.components.commands import CommandComposer
from edison.core.adapters.components.hooks import HookComposer
from edison.core.adapters.components.settings import SettingsComposer


class ClaudeAdapterError(RuntimeError):
    """Error in Claude adapter operations."""


class ClaudeAdapter(PlatformAdapter):
    """Platform adapter for Claude Code.

    This adapter:
    - Reads from _generated/ (already composed by unified engine)
    - Writes to .claude/ with Claude-specific formatting
    - Uses composition.yaml for all path configuration
    - Does NOT do composition itself

    Syncs:
    - CLAUDE.md client configuration
    - Agent files with frontmatter
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize Claude adapter.

        Args:
            project_root: Project root directory.
        """
        super().__init__(project_root=project_root)
        self.project_config_dir = get_project_config_dir(self.project_root)

        # Client config - NO fallback, config MUST exist
        self.claude_dir = self.adapters_config.get_client_path("claude")

        # Sync config for agents
        sync_cfg = self.output_config.get_sync_config("claude")
        if sync_cfg and sync_cfg.enabled and sync_cfg.agents_path:
            self.claude_agents_dir = self.output_config._resolve_path(sync_cfg.agents_path)
            self._agents_filename_pattern = sync_cfg.agents_filename_pattern or "{name}.md"
        else:
            self.claude_agents_dir = self.claude_dir / "agents"
            self._agents_filename_pattern = "{name}.md"

        # Components (platform-agnostic) using shared context
        self.commands = CommandComposer(self.context)
        self.hooks = HookComposer(self.context)
        self.settings = SettingsComposer(self.context)

    # =========================================================================
    # Platform Properties
    # =========================================================================

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "claude"

    # =========================================================================
    # Generated Content Directories
    # =========================================================================

    @property
    def generated_agents_dir(self) -> Path:
        """Path to _generated/agents/."""
        agents_dir = self.output_config.get_agents_dir()
        if agents_dir:
            return agents_dir
        return self.project_config_dir / "_generated" / "agents"

    @property
    def generated_clients_dir(self) -> Path:
        """Path to _generated/clients/."""
        return self.project_config_dir / "_generated" / "clients"

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_structure(
        self,
        *,
        create_missing: bool = True,
    ) -> Path:
        """Ensure .claude directory structure exists.

        Args:
            create_missing: Create directories if they don't exist.

        Returns:
            Path to the .claude directory.

        Raises:
            ClaudeAdapterError: If directory doesn't exist and create_missing=False.
        """
        if not self.claude_dir.exists():
            if not create_missing:
                raise ClaudeAdapterError(f"Missing: {self.claude_dir}")
            ensure_directory(self.claude_dir)

        if not self.claude_agents_dir.exists():
            if not create_missing:
                raise ClaudeAdapterError(f"Missing: {self.claude_agents_dir}")
            ensure_directory(self.claude_agents_dir)

        return self.claude_dir

    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_claude_md(self) -> Optional[Path]:
        """Sync client config to CLAUDE.md.

        Uses paths from composition.yaml configuration.

        Returns:
            Path to written file, or None if disabled or source doesn't exist.
        """
        client_cfg = self.output_config.get_client_config("claude")
        if client_cfg is None or not client_cfg.enabled:
            return None

        self.validate_structure()

        # Try to find source from _generated/clients/
        source = self.generated_clients_dir / "claude.md"
        if not source.exists():
            return None

        content = source.read_text(encoding="utf-8")
        target = self.output_config.get_client_path("claude")
        if target is None:
            return None

        ensure_directory(target.parent)
        self.writer.write_text(target, content)
        return target

    def sync_agents(self) -> List[Path]:
        """Sync _generated/agents/*.md to Claude agents directory with frontmatter.

        Uses paths from composition.yaml configuration.

        Returns:
            List of written agent files.
        """
        sync_cfg = self.output_config.get_sync_config("claude")
        if sync_cfg is None or not sync_cfg.enabled:
            return []

        self.validate_structure()

        if not self.generated_agents_dir.exists():
            return []

        written: List[Path] = []
        for source in sorted(self.generated_agents_dir.glob("*.md")):
            agent_name = source.stem
            content = source.read_text(encoding="utf-8")

            # Add Claude frontmatter
            rendered = self._add_frontmatter(agent_name, content)

            filename = self._agents_filename_pattern.format(name=agent_name)
            target = self.claude_agents_dir / filename
            self.writer.write_text(target, rendered)
            written.append(target)

        return written

    def sync_all(self) -> Dict[str, List[Path]]:
        """Sync all Edison outputs to Claude Code layout.

        Returns:
            Dict with 'claude_md' and 'agents' keys containing synced paths.
        """
        result: Dict[str, List[Path]] = {
            "claude_md": [],
            "agents": [],
            "commands": [],
            "hooks": [],
            "settings": [],
        }

        claude_md = self.sync_claude_md()
        if claude_md:
            result["claude_md"].append(claude_md)

        result["agents"] = self.sync_agents()

        # Commands
        commands = self.commands.compose_all().get("claude", {})
        result["commands"] = list(commands.values())

        # Hooks
        hooks = self.hooks.compose_hooks()
        result["hooks"] = list(hooks.values())

        # Settings
        settings_path = self.settings.write_settings_file()
        if settings_path:
            result["settings"].append(settings_path)
        return result

    # =========================================================================
    # Formatting Helpers
    # =========================================================================

    def _add_frontmatter(self, agent_name: str, content: str) -> str:
        """Add Claude Code frontmatter to agent content.

        Uses shared format_frontmatter for consistency.

        Args:
            agent_name: Name of the agent
            content: Original agent content

        Returns:
            Content with Claude frontmatter prepended
        """
        from edison.core.utils.text import format_frontmatter

        # Extract description from first non-empty, non-comment, non-heading line
        lines = content.strip().split("\n")
        description = f"{agent_name} agent"
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
                description = stripped[:100]
                break

        # Use shared frontmatter formatter
        frontmatter_data = {
            "name": agent_name,
            "description": description,
            "model": "sonnet",
        }
        frontmatter = format_frontmatter(frontmatter_data, exclude_none=True)

        return frontmatter + "\n" + content


__all__ = ["ClaudeAdapter", "ClaudeAdapterError"]
