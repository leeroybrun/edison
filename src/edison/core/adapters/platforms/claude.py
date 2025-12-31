"""Claude Code platform adapter.

Handles:
- Syncing Edison-composed outputs to Claude Code layout
- Adding Claude-specific frontmatter to agents
- Managing .claude/ directory structure
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.io import ensure_directory
from edison.core.adapters.components.commands import CommandComposer
from edison.core.adapters.components.hooks import HookComposer
from edison.core.adapters.components.settings import SettingsComposer

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class ClaudeAdapterError(RuntimeError):
    """Error in Claude adapter operations."""


class ClaudeAdapter(PlatformAdapter):
    """Platform adapter for Claude Code.

    This adapter:
    - Reads from _generated/ (already composed by unified engine)
    - Writes to .claude/ with Claude-specific formatting
    - Uses CompositionConfig for all path configuration
    - Does NOT do composition itself

    Syncs:
    - CLAUDE.md client configuration (via roots content_type)
    - Agent files with frontmatter
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> None:
        """Initialize Claude adapter.

        Args:
            project_root: Project root directory.
            adapter_config: Adapter configuration from loader.
        """
        super().__init__(project_root=project_root, adapter_config=adapter_config)
        self.project_config_dir = get_project_config_dir(self.project_root)

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

    @property
    def claude_dir(self) -> Path:
        """Path to .claude/ directory."""
        return self.get_output_path()

    @property
    def claude_agents_dir(self) -> Path:
        """Path to .claude/agents/ directory."""
        dest = self.get_sync_destination("agents")
        if dest:
            return dest
        return self.claude_dir / "agents"

    @property
    def agents_filename_pattern(self) -> str:
        """Filename pattern for agent files."""
        sync_cfg = self.get_sync_config("agents")
        if sync_cfg:
            return sync_cfg.filename_pattern
        return "{name}.md"

    # =========================================================================
    # Generated Content Directories
    # =========================================================================

    @property
    def generated_agents_dir(self) -> Path:
        """Path to _generated/agents/."""
        # Get from content_types config
        agents_cfg = self.composition_config.get_content_type("agents")
        if agents_cfg:
            return self.composition_config.resolve_output_path(agents_cfg.output_path)
        return self.project_config_dir / "_generated" / "agents"

    # =========================================================================
    # Validation
    # =========================================================================

    def ensure_structure(self, *, create_missing: bool = True) -> Path:
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

    def validate_structure(self, *, create_missing: bool = True) -> Path:
        """Back-compat alias for `ensure_structure` used by older tests/callers."""
        return self.ensure_structure(create_missing=create_missing)

    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_agents(self) -> List[Path]:
        """Sync _generated/agents/*.md to Claude agents directory with frontmatter.

        Uses paths from CompositionConfig.

        Returns:
            List of written agent files.
        """
        if not self.is_sync_enabled("agents"):
            return []

        self.ensure_structure()

        if not self.generated_agents_dir.exists():
            return []

        written: List[Path] = []
        for source in sorted(self.generated_agents_dir.glob("*.md")):
            agent_name = source.stem
            content = source.read_text(encoding="utf-8")

            # Add Claude frontmatter
            rendered = self._add_frontmatter(agent_name, content)

            filename = self.agents_filename_pattern.format(name=agent_name)
            target = self.claude_agents_dir / filename
            self.write_text_managed(target, rendered)
            written.append(target)

        return written

    def sync_claude_md(self) -> Path | None:
        """Sync CLAUDE.md client config into `.claude/CLAUDE.md`.

        Source resolution (fail-soft; first match wins):
        - `.edison/_generated/clients/claude.md` (legacy)
        - `.edison/_generated/roots/CLAUDE.md` (preferred)
        """
        self.ensure_structure()

        candidates = [
            self.project_dir / "_generated" / "clients" / "claude.md",
            self.project_dir / "_generated" / "roots" / "CLAUDE.md",
        ]
        source: Path | None = next((p for p in candidates if p.exists()), None)
        if source is None:
            return None

        target = self.claude_dir / "CLAUDE.md"
        content = source.read_text(encoding="utf-8", errors="strict")
        self.write_text_managed(target, content)
        return target

    def sync_all(self) -> Dict[str, List[Path]]:
        """Sync all Edison outputs to Claude Code layout.

        Returns:
            Dict with synced file paths by category.
        """
        result: Dict[str, List[Path]] = {
            "claude_md": [],
            "agents": [],
            "commands": [],
            "hooks": [],
            "settings": [],
        }

        maybe_claude_md = self.sync_claude_md()
        if maybe_claude_md is not None:
            result["claude_md"].append(maybe_claude_md)

        result["agents"] = self.sync_agents()

        # Commands
        definitions = self.commands.compose()
        commands = self.commands.compose_for_platform("claude", definitions)
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
        # Idempotency: modern Edison agent prompts already include YAML frontmatter.
        # If the file already starts with a frontmatter block, do not prepend another.
        stripped = content.lstrip()
        if stripped.startswith("---"):
            lines = stripped.splitlines()
            # Detect the closing delimiter within a small bound (avoid scanning huge files).
            for i in range(1, min(len(lines), 80)):
                if lines[i].strip() == "---":
                    return content

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
