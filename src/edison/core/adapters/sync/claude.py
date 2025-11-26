from __future__ import annotations

"""Claude Code sync adapter.

Syncs Edison-composed outputs into Claude Code layout.
All output paths are configurable via composition.yaml - NO hardcoded paths.

This adapter does NOT do composition - it only syncs pre-composed files
from the unified composition engine output.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ...paths import PathResolver
from ...paths.project import get_project_config_dir
from ...composition.output_config import OutputConfigLoader
from edison.core.file_io.utils import ensure_dir


class ClaudeAdapterError(RuntimeError):
    """Error in Claude adapter operations."""


class ClaudeSync:
    """Sync Edison-composed outputs to Claude Code layout.
    
    This adapter:
    - Reads from _generated/ (already composed by unified engine)
    - Writes to .claude/ with Claude-specific formatting
    - Uses composition.yaml for all path configuration
    - Does NOT do composition itself
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root: Path = repo_root or PathResolver.resolve_project_root()
        self.project_config_dir = get_project_config_dir(self.repo_root)
        self._config = OutputConfigLoader(repo_root=self.repo_root)
        
        # Source paths from config
        agents_dir = self._config.get_agents_dir()
        self.generated_agents_dir = agents_dir if agents_dir else (
            self.project_config_dir / "_generated" / "agents"
        )
        
        # Client config
        client_cfg = self._config.get_client_config("claude")
        if client_cfg and client_cfg.enabled:
            self.claude_dir = self._config._resolve_path(client_cfg.output_path)
        else:
            self.claude_dir = self.repo_root / ".claude"
        
        # Sync config for agents
        sync_cfg = self._config.get_sync_config("claude")
        if sync_cfg and sync_cfg.enabled and sync_cfg.agents_path:
            self.claude_agents_dir = self._config._resolve_path(sync_cfg.agents_path)
            self._agents_filename_pattern = sync_cfg.agents_filename_pattern or "{name}.md"
        else:
            self.claude_agents_dir = self.claude_dir / "agents"
            self._agents_filename_pattern = "{name}.md"

    def validate_structure(self, *, create_missing: bool = True) -> Path:
        """Ensure .claude directory structure exists.
        
        Args:
            create_missing: Create directories if they don't exist.
            
        Returns:
            Path to the .claude directory.
        """
        if not self.claude_dir.exists():
            if not create_missing:
                raise ClaudeAdapterError(f"Missing: {self.claude_dir}")
            ensure_dir(self.claude_dir)
        
        if not self.claude_agents_dir.exists():
            if not create_missing:
                raise ClaudeAdapterError(f"Missing: {self.claude_agents_dir}")
            ensure_dir(self.claude_agents_dir)
        
        return self.claude_dir

    def sync_claude_md(self) -> Optional[Path]:
        """Sync client config to CLAUDE.md.
        
        Uses paths from composition.yaml configuration.
        
        Returns:
            Path to written file, or None if disabled or source doesn't exist.
        """
        client_cfg = self._config.get_client_config("claude")
        if client_cfg is None or not client_cfg.enabled:
            return None
        
        self.validate_structure()
        
        # Try to find source from _generated/clients/
        source = self.project_config_dir / "_generated" / "clients" / "claude.md"
        if not source.exists():
            return None
        
        content = source.read_text(encoding="utf-8")
        target = self._config.get_client_path("claude")
        if target is None:
            return None
        
        ensure_dir(target.parent)
        target.write_text(content, encoding="utf-8")
        return target

    def sync_agents(self) -> List[Path]:
        """Sync _generated/agents/*.md to Claude agents directory with frontmatter.
        
        Uses paths from composition.yaml configuration.
        
        Returns:
            List of written agent files.
        """
        sync_cfg = self._config.get_sync_config("claude")
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
            target.write_text(rendered, encoding="utf-8")
            written.append(target)
        
        return written

    def sync_all(self) -> Dict[str, List[Path]]:
        """Sync all Edison outputs to Claude Code layout.
        
        Returns:
            Dict with 'claude_md' and 'agents' keys.
        """
        result: Dict[str, List[Path]] = {
            "claude_md": [],
            "agents": [],
        }
        
        claude_md = self.sync_claude_md()
        if claude_md:
            result["claude_md"].append(claude_md)
        
        result["agents"] = self.sync_agents()
        return result

    def _add_frontmatter(self, agent_name: str, content: str) -> str:
        """Add Claude Code frontmatter to agent content.
        
        Args:
            agent_name: Name of the agent
            content: Original agent content
            
        Returns:
            Content with Claude frontmatter prepended
        """
        # Extract description from first non-empty, non-comment, non-heading line
        lines = content.strip().split("\n")
        description = f"{agent_name} agent"
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
                description = stripped[:100]
                break
        
        frontmatter = f"""name: {agent_name}
description: {description}
model: sonnet
---

"""
        return frontmatter + content


__all__ = ["ClaudeSync", "ClaudeAdapterError"]
