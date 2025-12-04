"""Compose IDE slash commands for multiple platforms from unified definitions.

This module provides platform-agnostic command composition that works with
Claude Code, Cursor, and Codex.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from edison.core.composition.utils.paths import resolve_project_dir_placeholders
from edison.core.utils.io import ensure_directory
from .base import AdapterComponent, AdapterContext

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
class PlatformCommandAdapter(ABC):
    """Interface for per-platform command rendering."""

    name: str = "base"

    @abstractmethod
    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        """Render a command for this platform."""
        raise NotImplementedError

    @abstractmethod
    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        """Get output path for a command."""
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


class ClaudeCommandAdapter(PlatformCommandAdapter):
    """Claude Code platform renderer."""

    name = "claude"

    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        return _render_markdown(cmd, "Claude")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CursorCommandAdapter(PlatformCommandAdapter):
    """Cursor editor platform renderer."""

    name = "cursor"

    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        return _render_markdown(cmd, "Cursor")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CodexCommandAdapter(PlatformCommandAdapter):
    """Codex CLI platform renderer."""

    name = "codex"

    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        return _render_markdown(cmd, "Codex")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


# ---------- Composer ----------
from .base import AdapterComponent


class CommandComposer(AdapterComponent):
    """Compose slash commands for IDE platforms."""

    def __init__(
        self,
        context: AdapterContext,
    ) -> None:
        super().__init__(context)

        self.short_desc_max = self._short_desc_max()
        self.adapters: Dict[str, PlatformCommandAdapter] = {
            "claude": ClaudeCommandAdapter(),
            "cursor": CursorCommandAdapter(),
            "codex": CodexCommandAdapter(),
        }

    # ----- Public API -----
    def compose(self) -> List[CommandDefinition]:
        """Compose definitions (core → packs → project) and apply filtering."""
        return self.filter_definitions(self.load_definitions())

    def sync(self, output_dir: Path) -> List[Path]:
        """Sync commands for all configured platforms into a base output dir."""
        written: List[Path] = []
        definitions = self.compose()
        for platform in self._platforms():
            platform_results = self.compose_for_platform(platform, definitions)
            written.extend(platform_results.values())
        return written

    def load_definitions(self) -> List[CommandDefinition]:
        """Load and merge command definitions from core, packs, and project overrides."""
        merged: Dict[str, Dict[str, Any]] = {}

        def merge_from_file(base: Dict[str, Dict[str, Any]], path: Path) -> Dict[str, Dict[str, Any]]:
            data = self._load_yaml_commands(path)
            return self._merge_definitions_by_id(base, data, id_key="id")

        core_file = self.core_dir / "config" / "commands.yaml"
        merged = merge_from_file(merged, core_file)

        for pack in self.active_packs:
            pack_file = self.bundled_packs_dir / pack / "config" / "commands.yml"
            merged = merge_from_file(merged, pack_file)

        project_file = self.project_dir / "config" / "commands.yml"
        merged = merge_from_file(merged, project_file)

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

    def compose_for_platform(
        self, platform: str, defs: List[CommandDefinition]
    ) -> Dict[str, Path]:
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
            ensure_directory(out_path.parent)
            rendered = resolve_project_dir_placeholders(
                rendered,
                project_dir=self.project_dir,
                target_path=out_path,
                repo_root=self.project_root,
            )
            out_path.write_text(rendered, encoding="utf-8")
            results[cmd.id] = out_path
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
    def _load_yaml_commands(self, path: Path) -> List[Dict[str, Any]]:
        """Load command ``definitions`` list from YAML path (empty when missing)."""
        if not path.exists():
            return []

        data = self.context.cfg_mgr.load_yaml(path)
        if not isinstance(data, dict):
            return []

        commands = data.get("commands")

        # Schema: commands: { definitions: [...] }
        if isinstance(commands, dict):
            definitions = commands.get("definitions") or []
            if isinstance(definitions, list):
                return [c for c in definitions if isinstance(c, dict)]

        return []

    def _dicts_to_defs(self, merged: Dict[str, Dict[str, Any]]) -> List[CommandDefinition]:
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

    # ----- Internal merge helper -----
    def _merge_definitions_by_id(
        self,
        base: Dict[str, Dict[str, Any]],
        new_defs: List[Dict[str, Any]],
        id_key: str = "id",
    ) -> Dict[str, Dict[str, Any]]:
        """Merge list of definition dicts into base dict keyed by id."""
        result = dict(base)
        for def_dict in new_defs:
            if not isinstance(def_dict, dict):
                continue
            def_id = def_dict.get(id_key)
            if not def_id:
                continue
            existing = result.get(def_id, {})
            merged = self.context.cfg_mgr.deep_merge(existing, def_dict)
            result[def_id] = merged
        return result

    def _output_dir_for(self, platform: str) -> Path:
        commands_cfg = (self.config.get("commands") or {}) if self.config else {}
        out_cfg = commands_cfg.get("output_dirs") or {}
        override = out_cfg.get(platform)
        if override:
            return Path(str(Path(override).expanduser()))

        if platform == "claude":
            return self.project_root / ".claude" / "commands"
        if platform == "cursor":
            return self.project_root / ".cursor" / "commands"
        if platform == "codex":
            return self.project_root / ".codex" / "prompts"
        return self.project_root / "_commands" / platform

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
    config: Dict[str, Any],
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
    "PlatformCommandAdapter",
    "ClaudeCommandAdapter",
    "CursorCommandAdapter",
    "CodexCommandAdapter",
    "CommandComposer",
    "compose_commands",
]
