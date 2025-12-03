#!/usr/bin/env python3
from __future__ import annotations

"""Compose IDE slash commands for multiple platforms from unified definitions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from abc import ABC, abstractmethod

from edison.core.utils.io import ensure_directory
from ..path_utils import resolve_project_dir_placeholders
from .base import IDEComposerBase

# Defaults
DEFAULT_SHORT_DESC_MAX = 80
DEFAULT_PLATFORMS = ["claude", "cursor", "codex"]


# ---------- Data classes ----------
@dataclass
class CommandArg:
    """Command argument definition."""

    name: str
    description: str
    required: bool = True


@dataclass
class CommandDefinition:
    """Platform-agnostic command definition."""

    id: str
    domain: str
    command: str
    short_desc: str  # < 80 chars for system prompt
    full_desc: str
    cli: str
    args: List[CommandArg]
    when_to_use: str
    related_commands: List[str]


# ---------- Platform adapters ----------
class PlatformAdapter(ABC):
    """Interface for per-platform command rendering."""

    name: str = "base"

    @abstractmethod
    def render_command(self, cmd: CommandDefinition, config: Dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        raise NotImplementedError


def _render_markdown(cmd: CommandDefinition, platform_label: str) -> str:
    """Shared Markdown renderer for command definitions."""
    arg_lines = []
    for arg in cmd.args:
        flag = "required" if arg.required else "optional"
        arg_lines.append(f"- {arg.name} ({flag}): {arg.description}")

    related = ", ".join(cmd.related_commands) if cmd.related_commands else "None"

    sections = [
        f"# {cmd.command} [{platform_label}]",
        cmd.short_desc,
        "",
        "## CLI",
        f"`{cmd.cli}`",
        "",
        "## Arguments",
        "\n".join(arg_lines) if arg_lines else "None",
        "",
        "## When to use",
        cmd.when_to_use,
        "",
        "## Full description",
        cmd.full_desc,
        "",
        "## Related",
        related,
    ]
    return "\n".join(sections).strip() + "\n"


class ClaudeCommandAdapter(PlatformAdapter):
    """Claude Code platform renderer."""

    name = "claude"

    def render_command(self, cmd: CommandDefinition, config: Dict) -> str:
        return _render_markdown(cmd, "Claude")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CursorCommandAdapter(PlatformAdapter):
    """Cursor editor platform renderer."""

    name = "cursor"

    def render_command(self, cmd: CommandDefinition, config: Dict) -> str:
        return _render_markdown(cmd, "Cursor")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CodexCommandAdapter(PlatformAdapter):
    """Codex CLI platform renderer."""

    name = "codex"

    def render_command(self, cmd: CommandDefinition, config: Dict) -> str:
        return _render_markdown(cmd, "Codex")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


# ---------- Composer ----------
class CommandComposer(IDEComposerBase):
    """Compose slash commands for IDE platforms."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        super().__init__(config=config, repo_root=repo_root)
        self.short_desc_max = self._short_desc_max()
        self.adapters: Dict[str, PlatformAdapter] = {
            "claude": ClaudeCommandAdapter(),
            "cursor": CursorCommandAdapter(),
            "codex": CodexCommandAdapter(),
        }

    # ----- Public API -----
    def load_definitions(self) -> List[CommandDefinition]:
        """Load and merge command definitions from core, packs, and project overrides.

        Uses unified _load_layered_config() to load from all layers, but handles
        list-based command definitions with special merging by id.

        Note: Commands use a list-based schema (commands.definitions: [...]), so we
        load each layer separately and merge the lists manually rather than relying
        on deep_merge which would replace lists.
        """
        merged: Dict[str, Dict] = {}

        # Load and merge from each layer manually (commands need list merging by id)
        # Load .yaml first, then .yml to allow .yml to override .yaml
        # 1. Core layer
        core_yaml = self.core_dir / "config" / "commands.yaml"
        if core_yaml.exists():
            core_data = self._extract_command_definitions(self.load_yaml_safe(core_yaml))
            merged = self._merge_command_list(merged, core_data)

        core_yml = self.core_dir / "config" / "commands.yml"
        if core_yml.exists():
            core_data = self._extract_command_definitions(self.load_yaml_safe(core_yml))
            merged = self._merge_command_list(merged, core_data)

        # 2. Pack layers
        for pack in self.get_active_packs():
            # Bundled pack (.yaml then .yml)
            pack_yaml = self.bundled_packs_dir / pack / "config" / "commands.yaml"
            if pack_yaml.exists():
                pack_data = self._extract_command_definitions(self.load_yaml_safe(pack_yaml))
                merged = self._merge_command_list(merged, pack_data)

            pack_yml = self.bundled_packs_dir / pack / "config" / "commands.yml"
            if pack_yml.exists():
                pack_data = self._extract_command_definitions(self.load_yaml_safe(pack_yml))
                merged = self._merge_command_list(merged, pack_data)

            # Project pack (.yaml then .yml)
            project_pack_yaml = self.project_packs_dir / pack / "config" / "commands.yaml"
            if project_pack_yaml.exists():
                project_pack_data = self._extract_command_definitions(self.load_yaml_safe(project_pack_yaml))
                merged = self._merge_command_list(merged, project_pack_data)

            project_pack_yml = self.project_packs_dir / pack / "config" / "commands.yml"
            if project_pack_yml.exists():
                project_pack_data = self._extract_command_definitions(self.load_yaml_safe(project_pack_yml))
                merged = self._merge_command_list(merged, project_pack_data)

        # 3. Project layer (load .yaml first, then .yml to allow .yml to override)
        project_yaml = self.project_dir / "config" / "commands.yaml"
        if project_yaml.exists():
            project_data = self._extract_command_definitions(self.load_yaml_safe(project_yaml))
            merged = self._merge_command_list(merged, project_data)

        project_yml = self.project_dir / "config" / "commands.yml"
        if project_yml.exists():
            project_data = self._extract_command_definitions(self.load_yaml_safe(project_yml))
            merged = self._merge_command_list(merged, project_data)

        return self._dicts_to_defs(merged)

    def filter_definitions(self, defs: List[CommandDefinition]) -> List[CommandDefinition]:
        """Apply selection strategy defined in configuration."""
        selection = ((self.config or {}).get("commands") or {}).get("selection", {})
        mode = (selection or {}).get("mode", "all")
        if mode == "domains":
            allowed = set(selection.get("domains") or [])
            return [d for d in defs if d.domain in allowed]
        if mode == "explicit":
            ids = set(selection.get("ids") or selection.get("commands") or [])
            return [d for d in defs if d.id in ids]
        return defs

    def compose_for_platform(self, platform: str, defs: List[CommandDefinition]) -> Dict[str, Path]:
        """Render and write commands for a single platform."""
        key = platform.lower()
        if key not in self.adapters:
            raise ValueError(f"Unsupported platform: {platform}")

        adapter = self.adapters[key]
        output_dir = ensure_directory(self._output_dir_for(key))

        results: Dict[str, Path] = {}
        for cmd in defs:
            rendered = adapter.render_command(cmd, self.config.get("commands", {}))
            out_path = adapter.get_output_path(cmd.id, output_dir)
            rendered = resolve_project_dir_placeholders(
                rendered,
                project_dir=self.project_dir,
                target_path=out_path,
                repo_root=self.repo_root,
            )
            written_path = self.writer.write_text(out_path, rendered)
            results[cmd.id] = written_path
        return results

    def compose_all(self) -> Dict[str, Dict[str, Path]]:
        """Compose commands for all configured platforms."""
        definitions = self.filter_definitions(self.load_definitions())
        platforms = self._platforms()

        results: Dict[str, Dict[str, Path]] = {}
        for platform in platforms:
            results[platform] = self.compose_for_platform(platform, definitions)
        return results

    # ----- Helpers -----
    def _extract_command_definitions(self, data: Dict) -> List[Dict]:
        """Extract command definitions list from loaded config data.

        Args:
            data: Config data (could be from file or _load_layered_config())

        Returns:
            List of command definition dicts
        """
        if not isinstance(data, dict):
            return []

        commands = data.get("commands")

        # Schema: commands: { definitions: [...] }
        if isinstance(commands, dict):
            definitions = commands.get("definitions") or []
            if isinstance(definitions, list):
                return [c for c in definitions if isinstance(c, dict)]

        return []

    def _merge_command_list(self, merged: Dict[str, Dict], commands_list: List[Dict]) -> Dict[str, Dict]:
        """Merge a list of command definitions into the merged dict by id.

        Args:
            merged: Existing merged commands dict (keyed by id)
            commands_list: New commands list to merge in

        Returns:
            Updated merged dict
        """
        for cmd_dict in commands_list:
            if not isinstance(cmd_dict, dict):
                continue
            cmd_id = cmd_dict.get("id")
            if not cmd_id:
                continue
            existing = merged.get(cmd_id, {})
            merged[cmd_id] = self.cfg_mgr.deep_merge(existing, cmd_dict)
        return merged

    def _dicts_to_defs(self, merged: Dict[str, Dict]) -> List[CommandDefinition]:
        """Convert merged dicts to dataclass instances."""
        defs: List[CommandDefinition] = []
        for cmd_id, raw in merged.items():
            short_desc = self._truncate_short_desc(str(raw.get("short_desc", "")))
            args_raw = raw.get("args") or []
            args: List[CommandArg] = []
            for arg in args_raw:
                if not isinstance(arg, dict):
                    continue
                args.append(
                    CommandArg(
                        name=str(arg.get("name", "")),
                        description=str(arg.get("description", "")),
                        required=bool(arg.get("required", True)),
                    )
                )
            defs.append(
                CommandDefinition(
                    id=str(cmd_id),
                    domain=str(raw.get("domain", "")),
                    command=str(raw.get("command", "")),
                    short_desc=short_desc,
                    full_desc=str(raw.get("full_desc", "")),
                    cli=str(raw.get("cli", "")),
                    args=args,
                    when_to_use=str(raw.get("when_to_use", "")),
                    related_commands=list(raw.get("related_commands") or []),
                )
            )
        return sorted(defs, key=lambda d: d.id)

    def _output_dir_for(self, platform: str) -> Path:
        commands_cfg = (self.config.get("commands") or {}) if self.config else {}
        out_cfg = commands_cfg.get("output_dirs") or {}
        override = out_cfg.get(platform)
        if override:
            return Path(str(Path(override).expanduser()))

        if platform == "claude":
            return self.repo_root / ".claude" / "commands"
        if platform == "cursor":
            return self.repo_root / ".cursor" / "commands"
        if platform == "codex":
            return Path.home() / ".codex" / "prompts"
        return self.repo_root / "_commands" / platform

    def _platforms(self) -> List[str]:
        commands_cfg = (self.config.get("commands") or {}) if self.config else {}
        platforms = commands_cfg.get("platforms")
        if isinstance(platforms, list) and platforms:
            return [str(p).lower() for p in platforms]
        return list(DEFAULT_PLATFORMS)

    def _short_desc_max(self) -> int:
        commands_cfg = (self.config.get("commands") or {}) if self.config else {}
        raw = (
            commands_cfg.get("short_desc_max")
            or commands_cfg.get("shortDescMax")
            or DEFAULT_SHORT_DESC_MAX
        )
        try:
            return int(raw)
        except Exception:
            return DEFAULT_SHORT_DESC_MAX

    def _truncate_short_desc(self, text: str) -> str:
        if len(text) <= self.short_desc_max:
            return text
        return text[: self.short_desc_max - 3].rstrip() + "..."


def compose_commands(
    config: Dict,
    platforms: Optional[List[str]] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Dict[str, Path]]:
    """Functional helper to compose commands across one or more platforms.

    Args:
        config: Fully merged Edison configuration.
        platforms: Optional platform whitelist. When ``None``, uses the
            configured platform list or the default set.
        repo_root: Repository root for resolution; when omitted, auto-detected.
    """

    composer = CommandComposer(config=config, repo_root=repo_root)
    definitions = composer.filter_definitions(composer.load_definitions())

    target_platforms: List[str]
    if platforms is None:
        target_platforms = composer._platforms()
    else:
        target_platforms = [p.lower() for p in platforms]

    results: Dict[str, Dict[str, Path]] = {}
    for platform in target_platforms:
        results[platform] = composer.compose_for_platform(platform, definitions)
    return results


__all__ = [
    "CommandArg",
    "CommandDefinition",
    "PlatformAdapter",
    "ClaudeCommandAdapter",
    "CursorCommandAdapter",
    "CodexCommandAdapter",
    "CommandComposer",
    "compose_commands",
]



