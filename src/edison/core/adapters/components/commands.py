"""Compose IDE slash commands for multiple platforms from unified definitions.

This component generates per-platform "slash commands" using unified YAML
definitions (core → packs → user → project) plus per-platform render configuration.

Design goals (see docs/CONFIGURATION.md, docs/ARCHITECTURE.md):
- One canonical command definition list (commands.yaml)
- Per-platform formatting via Jinja templates
- Per-platform output dirs, prefixes, and truncation limits
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Optional dependency; fall back to basic rendering when absent
    from jinja2 import Template  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    Template = None  # type: ignore[assignment]

from edison.core.composition.utils.paths import resolve_project_dir_placeholders
from edison.core.utils.io import ensure_directory
from edison.data import get_data_path
from .base import AdapterComponent, AdapterContext


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


# ---------------------------------------------------------------------------
# Legacy per-platform adapters (kept for backwards compatibility)
# ---------------------------------------------------------------------------

class PlatformCommandAdapter(ABC):
    """Legacy interface for per-platform command rendering.

    Modern Edison uses per-platform Jinja templates via CommandComposer.
    These adapters remain for older call sites and skipped legacy tests.
    """

    name: str = "base"

    @abstractmethod
    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        raise NotImplementedError


def _render_markdown(cmd: CommandDefinition, platform_label: str) -> str:
    arg_lines: List[str] = []
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
    name = "claude"

    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        return _render_markdown(cmd, "Claude")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CursorCommandAdapter(PlatformCommandAdapter):
    name = "cursor"

    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        return _render_markdown(cmd, "Cursor")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CodexCommandAdapter(PlatformCommandAdapter):
    name = "codex"

    def render_command(self, cmd: CommandDefinition, config: Dict[str, Any]) -> str:
        return _render_markdown(cmd, "Codex")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


# ---------- Composer ----------
class CommandComposer(AdapterComponent):
    """Compose slash commands for IDE platforms."""

    def __init__(
        self,
        context: AdapterContext,
    ) -> None:
        super().__init__(context)
        self._templates_dir = Path(get_data_path("templates", "commands"))

    # ----- Public API -----
    def compose(self) -> List[CommandDefinition]:
        """Compose definitions (core → packs → user → project) and apply filtering."""
        if not self._enabled():
            return []
        return self.filter_definitions(self.load_definitions())

    def sync(self, output_dir: Path) -> List[Path]:
        """Sync commands into a caller-provided base dir.

        Writes commands under `<output_dir>/<platform>/...` for each platform.
        """
        written: List[Path] = []
        definitions = self.compose()
        for platform in self._platforms():
            platform_results = self.compose_for_platform(
                platform,
                definitions,
                output_dir_override=Path(output_dir) / platform,
            )
            written.extend(platform_results.values())
        return written

    def load_definitions(self) -> List[CommandDefinition]:
        """Load command definitions using ConfigManager's pack-aware loading.

        ConfigManager handles the full layering:
        1. Core config (bundled commands.yaml)
        2. Pack configs (bundled + project packs)
        3. Project config (<project-config-dir>/config/commands.yaml)

        Note: Command definitions are merged by ID - if multiple sources define
        the same command ID, later sources override earlier ones.
        """
        from edison.core.config import ConfigManager

        cfg_mgr = ConfigManager(repo_root=self.project_root)
        full_config = cfg_mgr.load_config(validate=False, include_packs=True)

        commands_section = full_config.get("commands", {}) or {}
        definitions_list = commands_section.get("definitions", []) or []

        # Merge by ID - later definitions override earlier ones
        merged: Dict[str, Dict[str, Any]] = {}
        for defn in definitions_list:
            if isinstance(defn, dict) and defn.get("id"):
                cmd_id = str(defn["id"])
                if cmd_id in merged:
                    # Merge properties, later wins
                    merged[cmd_id] = {**merged[cmd_id], **defn}
                else:
                    merged[cmd_id] = dict(defn)

        return self._dicts_to_defs(merged)

    def filter_definitions(self, defs: List[CommandDefinition]) -> List[CommandDefinition]:
        """Apply selection strategy defined in configuration."""
        selection = (self._commands_cfg().get("selection") or {}) if self.config else {}
        mode = (selection or {}).get("mode", "all")
        excluded_domains = set(selection.get("exclude") or [])

        if mode == "domains":
            allowed = set(selection.get("domains") or [])
            return [d for d in defs if d.domain in allowed and d.domain not in excluded_domains]
        if mode == "explicit":
            ids = set(selection.get("ids") or selection.get("commands") or [])
            return [d for d in defs if d.id in ids and d.domain not in excluded_domains]
        return [d for d in defs if d.domain not in excluded_domains]

    def compose_for_platform(
        self,
        platform: str,
        defs: List[CommandDefinition],
        *,
        output_dir_override: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """Render and write commands for a single platform."""
        key = platform.lower()
        if key not in {"claude", "cursor", "codex"}:
            raise ValueError(f"Unsupported platform: {platform}")

        if not self._enabled():
            return {}

        platform_cfg = self._platform_cfg(key)
        if platform_cfg.get("enabled") is False:
            return {}

        output_dir = ensure_directory(self._output_dir_for(key, override=output_dir_override))
        prefix = str(platform_cfg.get("prefix") or "")
        template_name = str(platform_cfg.get("template") or self._default_template_name(key))
        max_short_desc = self._max_short_desc_for(key)

        template_path = self._resolve_template(template_name)
        template_text = template_path.read_text(encoding="utf-8")
        template = Template(template_text) if Template is not None else None

        results: Dict[str, Path] = {}
        for cmd in defs:
            display_name = f"{prefix}{cmd.id}"

            related = self._normalize_related_commands(cmd.related_commands, prefix=prefix)
            short_desc = self._truncate(str(cmd.short_desc or ""), max_short_desc)

            context: Dict[str, Any] = {
                "name": display_name,
                "short_desc": short_desc,
                "full_desc": str(cmd.full_desc or ""),
                "cli": str(cmd.cli or ""),
                "args": cmd.args,
                "when_to_use": str(cmd.when_to_use or ""),
                "related_commands": related,
                "platform": key,
                "platform_config": platform_cfg,
                "global_config": self.config,
                "command": cmd,
            }

            if template is not None:
                rendered = template.render(**context).rstrip() + "\n"
            else:
                # Minimal fallback when Jinja2 is unavailable.
                rendered = f"# {display_name}\n\n{cmd.full_desc}\n"

            out_path = output_dir / f"{display_name}.md"
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
    def _dicts_to_defs(self, merged: Dict[str, Dict[str, Any]]) -> List[CommandDefinition]:
        """Convert merged dicts to dataclass instances."""
        defs: List[CommandDefinition] = []
        for cmd_id, raw in merged.items():
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
                    short_desc=str(raw.get("short_desc", "")),
                    full_desc=str(raw.get("full_desc", "")),
                    cli=str(raw.get("cli", "")),
                    args=args,
                    when_to_use=str(raw.get("when_to_use", "")),
                    related_commands=list(raw.get("related_commands") or []),
                )
            )
        return sorted(defs, key=lambda d: d.id)

    def _output_dir_for(self, platform: str, *, override: Optional[Path] = None) -> Path:
        if override is not None:
            return Path(override)

        platform_cfg = self._platform_cfg(platform)
        out = platform_cfg.get("output_dir")
        if out:
            return Path(str(Path(str(out)).expanduser()))

        # Conservative defaults (repo-local) when no config is available.
        if platform == "claude":
            return self.project_root / ".claude" / "commands"
        if platform == "cursor":
            return self.project_root / ".cursor" / "commands"
        if platform == "codex":
            return self.project_root / ".codex" / "prompts"
        return self.project_root / "_commands" / platform

    def _platforms(self) -> List[str]:
        if not self._enabled():
            return []

        commands_cfg = self._commands_cfg()
        platforms = commands_cfg.get("platforms")
        if isinstance(platforms, list) and platforms:
            raw = [str(p).lower() for p in platforms]
        else:
            raw = ["claude", "cursor", "codex"]

        # Filter out explicitly disabled platform configs
        out: List[str] = []
        for p in raw:
            if self._platform_cfg(p).get("enabled") is False:
                continue
            out.append(p)
        return out

    def _enabled(self) -> bool:
        commands_cfg = self._commands_cfg()
        return commands_cfg.get("enabled") is not False

    def _commands_cfg(self) -> Dict[str, Any]:
        return (self.config or {}).get("commands", {}) or {}

    def _platform_cfg(self, platform: str) -> Dict[str, Any]:
        return (self._commands_cfg().get("platform_config", {}) or {}).get(platform, {}) or {}

    def _default_template_name(self, platform: str) -> str:
        if platform == "claude":
            return "claude-command.md.template"
        if platform == "cursor":
            return "cursor-command.md.template"
        return "codex-prompt.md.template"

    def _max_short_desc_for(self, platform: str) -> int:
        raw = self._platform_cfg(platform).get("max_short_desc")
        try:
            return int(raw) if raw is not None else 80
        except Exception:
            return 80

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if limit <= 0:
            return ""
        if len(text) <= limit:
            return text
        if limit <= 3:
            return text[:limit]
        return text[: limit - 3].rstrip() + "..."

    @staticmethod
    def _normalize_related_commands(related: List[str], *, prefix: str) -> List[str]:
        out: List[str] = []
        for item in related or []:
            s = str(item or "").strip()
            if not s:
                continue
            # If already prefixed, keep it; otherwise apply platform prefix.
            if prefix and not s.startswith(prefix):
                out.append(prefix + s)
            else:
                out.append(s)
        return out

    def _resolve_template(self, name: str) -> Path:
        if not name:
            raise ValueError("Command template name is required")

        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(self.project_root)

        # Priority (highest → lowest):
        # - overlay layer templates (project → user → company → ...)
        # - pack templates (higher pack root overrides lower)
        # - bundled Edison templates
        candidates: List[Path] = []

        for _layer_id, layer_root in reversed(resolver.overlay_layers):
            candidates.append(layer_root / "templates" / "commands" / name)

        # Pack templates in reverse order (later packs override earlier ones).
        # Within a given pack name, precedence is highest pack root first.
        for pack in reversed(self.active_packs):
            for root in reversed(resolver.pack_roots):
                candidates.append(root.path / pack / "templates" / "commands" / name)

        candidates.append(self._templates_dir / name)

        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"Command template not found: {name}")


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
    # Build a minimal component context so CommandComposer can read config.
    # This helper is primarily for legacy call sites; prefer the adapter-driven
    # interface (PlatformAdapter.context + CommandComposer) in new code.
    from edison.core.adapters.base import PlatformAdapter

    class _ComposeCommandsAdapter(PlatformAdapter):
        @property
        def platform_name(self) -> str:
            return "compose-commands"

        def sync_all(self) -> Dict[str, Any]:
            return {}

    root = (repo_root or Path.cwd()).resolve()
    adapter = _ComposeCommandsAdapter(project_root=root)
    adapter.config = adapter.cfg_mgr.deep_merge(adapter.config, config)
    composer = CommandComposer(adapter.context)
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
