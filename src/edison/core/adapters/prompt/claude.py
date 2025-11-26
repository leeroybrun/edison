from __future__ import annotations

"""
Claude prompt adapter.

Projects Edison `_generated` artifacts into the `.claude/` directory:
  - Orchestrator: `.claude/CLAUDE.md`
  - Agents: `.claude/agents/<agent>.md`

This adapter is intentionally thin:
  - Reads orchestrator guide + manifest from `<project_config_dir>/_generated/`
  - Delegates rich agent conversion to `ClaudeSync` (full-featured adapter) where
    appropriate so we preserve existing front‑matter semantics.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..base import PromptAdapter
from .._config import ConfigMixin


class ClaudeAdapter(PromptAdapter, ConfigMixin):
    """Provider adapter for Claude Code prompts."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root)
        # Initialize ConfigMixin cache
        self._cached_config: Optional[Dict] = None
        self.claude_dir = self.repo_root / ".claude"

    def render_orchestrator(self, guide_path: Path, manifest_path: Path) -> str:
        guide = guide_path.read_text(encoding="utf-8")
        # Manifest currently isn't required for rendering, but we validate
        # that it is readable to surface schema issues early.
        try:
            json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            # Soft-fail: allow orchestrator generation even if manifest is
            # malformed; downstream validators will surface details.
            pass

        header_lines: List[str] = [
            "# Claude Code Orchestrator",
            "<!-- GENERATED - DO NOT EDIT -->",
            f"<!-- Source: {guide_path.relative_to(self.repo_root)} -->",
            "<!-- Regenerate: scripts/prompts/compose --claude -->",
            "",
        ]

        # Preserve the curated Claude Orchestrator Brief from packs, when present.
        core_brief = self.repo_root / ".edison" / "packs" / "clients" / "claude" / "CLAUDE.md"
        if core_brief.exists():
            brief_text = core_brief.read_text(encoding="utf-8").strip()
            if brief_text:
                header_lines.append(brief_text)
                header_lines.append("")
                header_lines.append("---")
                header_lines.append("")

        header_lines.append("# Edison Orchestrator Guide (Generated)")
        header_lines.append("")
        header_lines.append(guide.strip())

        return "\n".join(header_lines).rstrip() + "\n"

    def render_agent(self, agent_name: str) -> str:
        """Render a minimal Claude agent wrapper from `_generated/agents`."""
        src = self.agents_dir / f"{agent_name}.md"
        if not src.exists():
            raise FileNotFoundError(f"Agent not found in _generated: {src}")

        body = src.read_text(encoding="utf-8").strip()
        lines: List[str] = [
            f"# {agent_name}",
            "<!-- GENERATED from Edison composition (_generated/agents) -->",
            "",
            body,
        ]
        return "\n".join(lines).rstrip() + "\n"

    def render_validator(self, validator_name: str) -> str:
        """Render validator prompts when `_generated/validators` is available."""
        src = self.validators_dir / f"{validator_name}.md"
        if not src.exists():
            raise FileNotFoundError(f"Validator not found in _generated: {src}")
        text = src.read_text(encoding="utf-8").strip()
        lines = [
            f"# Validator: {validator_name}",
            "<!-- GENERATED from Edison composition (_generated/validators) -->",
            "",
            text,
        ]
        return "\n".join(lines).rstrip() + "\n"

    def generate_commands(self) -> Dict[str, Path]:
        """Generate slash commands for Claude Code."""
        if not self.config.get("commands", {}).get("enabled"):
            return {}

        from ...composition.commands import CommandComposer

        composer = CommandComposer(self.config, self.repo_root)
        commands = composer.compose_for_platform("claude", composer.load_definitions())

        return commands

    def generate_hooks(self) -> Dict[str, Path]:
        """Generate hook scripts for Claude Code."""
        if not self.config.get("hooks", {}).get("enabled"):
            return {}

        from ...composition.hooks import HookComposer

        composer = HookComposer(self.config, self.repo_root)
        hooks = composer.compose_hooks()

        return hooks

    def generate_settings(self) -> Optional[Path]:
        """Generate settings.json for Claude Code."""
        claude_settings = self.config.get("settings", {}).get("claude", {})
        if not claude_settings.get("generate"):
            return None

        from ...composition.settings import SettingsComposer

        composer = SettingsComposer(self.config, self.repo_root)

        return composer.write_settings_file()

    def write_outputs(self, output_root: Path) -> None:
        """Write orchestrator + agents + commands + hooks + settings."""
        output_root.mkdir(parents=True, exist_ok=True)

        # Existing: Orchestrator
        guide = self.orchestrator_guide_path
        manifest = self.orchestrator_manifest_path
        if guide.exists() and manifest.exists():
            orchestrator_text = self.render_orchestrator(guide, manifest)
            (output_root / "CLAUDE.md").write_text(orchestrator_text, encoding="utf-8")

        # Existing: Agents - delegate to ClaudeSync for rich frontmatter
        from ..sync.claude import ClaudeSync
        adapter = ClaudeSync(repo_root=self.repo_root)
        adapter.sync_agents_to_claude()

        # NEW: Commands
        commands = self.generate_commands()
        if commands:
            print(f"✅ Generated {len(commands)} Claude Code commands")

        # NEW: Hooks
        hooks = self.generate_hooks()
        if hooks:
            print(f"✅ Generated {len(hooks)} Claude Code hooks")

        # NEW: Settings
        settings_path = self.generate_settings()
        if settings_path:
            print(f"✅ Generated Claude Code settings.json")

    # Config loading methods inherited from ConfigMixin


__all__ = ["ClaudeAdapter"]
