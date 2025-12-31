"""Compose IDE slash commands for multiple platforms.

This component generates per-platform "slash commands" from layered *markdown*
command definition files (core → packs → user → project) plus per-platform render
configuration from `config/commands.yaml`.

Design goals (see docs/CONFIGURATION.md, docs/ARCHITECTURE.md):
- Command definitions live in `commands/**` as individual markdown files (layerable)
- Per-platform formatting via Jinja templates
- Per-platform output dirs, prefixes, and truncation limits
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # Optional dependency; fall back to basic rendering when absent
    from jinja2 import Environment  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    Environment = None  # type: ignore[assignment]

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
    args: list[CommandArg]
    when_to_use: str
    related_commands: list[str]


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
    def render_command(self, cmd: CommandDefinition, config: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        raise NotImplementedError


def _render_markdown(cmd: CommandDefinition, platform_label: str) -> str:
    arg_lines: list[str] = []
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

    def render_command(self, cmd: CommandDefinition, config: dict[str, Any]) -> str:
        return _render_markdown(cmd, "Claude")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CursorCommandAdapter(PlatformCommandAdapter):
    name = "cursor"

    def render_command(self, cmd: CommandDefinition, config: dict[str, Any]) -> str:
        return _render_markdown(cmd, "Cursor")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


class CodexCommandAdapter(PlatformCommandAdapter):
    name = "codex"

    def render_command(self, cmd: CommandDefinition, config: dict[str, Any]) -> str:
        return _render_markdown(cmd, "Codex")

    def get_output_path(self, cmd_id: str, output_dir: Path) -> Path:
        return Path(output_dir) / f"{cmd_id}.md"


# ---------- Composer ----------
class CommandComposer(AdapterComponent):
    """Compose slash commands for IDE platforms."""

    _GENERATED_MARKERS: tuple[str, ...] = (
        "edison-generated: true",
        "EDISON:GENERATED",
    )

    def __init__(
        self,
        context: AdapterContext,
    ) -> None:
        super().__init__(context)
        self._templates_dir = Path(get_data_path("templates", "commands"))

    # ----- Public API -----
    def compose(self) -> list[CommandDefinition]:
        """Compose definitions (core → packs → user → project) and apply filtering."""
        if not self._enabled():
            return []
        return self.filter_definitions(self.load_definitions())

    def sync(self, output_dir: Path) -> list[Path]:
        """Sync commands into a caller-provided base dir.

        Writes commands under `<output_dir>/<platform>/...` for each platform.
        """
        written: list[Path] = []
        definitions = self.compose()
        for platform in self._platforms():
            platform_results = self.compose_for_platform(
                platform,
                definitions,
                output_dir_override=Path(output_dir) / platform,
            )
            written.extend(platform_results.values())
        return written

    def load_definitions(self) -> list[CommandDefinition]:
        """Load command definitions from layered markdown files (NO LEGACY).

        Source order (low → high precedence):
        - Core: <core_dir>/commands/**
        - Active packs: <{bundled,user,project}_packs_dir>/<pack>/commands/**
        - User: <user_dir>/commands/**
        - Project: <project_dir>/commands/**

        Later sources override earlier ones by `id`.
        """
        merged: dict[str, CommandDefinition] = {}
        for path in self._iter_definition_files():
            definition = self._parse_definition_file(path)
            if definition is None:
                continue
            merged[definition.id] = definition
        return sorted(merged.values(), key=lambda d: d.id)

    def filter_definitions(self, defs: list[CommandDefinition]) -> list[CommandDefinition]:
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
        defs: list[CommandDefinition],
        *,
        output_dir_override: Path | None = None,
    ) -> dict[str, Path]:
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
        template = None
        if Environment is not None:
            # Our templates use control blocks (`{% if ... %}`) on their own lines.
            # Without trimming, those lines become blank lines in rendered output.
            env = Environment(trim_blocks=True, lstrip_blocks=True)
            template = env.from_string(template_text)

        results: dict[str, Path] = {}
        expected_stems: set[str] = set()
        for cmd in defs:
            display_name = f"{prefix}{cmd.id}"
            expected_stems.add(display_name)

            related = self._normalize_related_commands(cmd.related_commands, prefix=prefix)
            short_desc = self._truncate(str(cmd.short_desc or ""), max_short_desc)

            context: dict[str, Any] = {
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

        self._prune_stale_generated_files(output_dir, expected_stems=expected_stems, prefix=prefix)
        return results

    def _prune_stale_generated_files(self, output_dir: Path, *, expected_stems: set[str], prefix: str) -> None:
        """Remove stale Edison-generated command files.

        Only deletes files that:
        - are not part of the current composed set, and
        - are Edison-generated (marker-based; with a conservative legacy fallback).
        """
        prefixes = [p for p in [prefix, *self._legacy_prefixes(prefix)] if p]

        for path in output_dir.glob("*.md"):
            if path.stem in expected_stems:
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue

            # Marker-based pruning is always safe (even when prefix="" or prefix conventions changed).
            if any(marker in content for marker in self._GENERATED_MARKERS):
                try:
                    path.unlink()
                except Exception:
                    continue
                continue

            # Conservative legacy pruning: only attempt prefix-based heuristics when we have an
            # explicit prefix to compare against.
            for active_prefix in prefixes:
                if self._is_edison_generated_content(content, prefix=active_prefix):
                    try:
                        path.unlink()
                    except Exception:
                        pass
                    break

    @staticmethod
    def _legacy_prefixes(prefix: str) -> list[str]:
        """Known prefix variants to prune when prefix conventions change.

        Edison historically used `edison-...` and now prefers `edison....` (per
        Speckit-style namespace prefixes). When switching conventions, stale
        files from the previous prefix should be removed.
        """
        p = str(prefix or "")
        if not p:
            return []

        out: list[str] = []
        if p.endswith("."):
            out.append(p[:-1] + "-")
        elif p.endswith("-"):
            out.append(p[:-1] + ".")
        return out

    def _is_edison_generated_content(self, content: str, *, prefix: str) -> bool:
        """Heuristic to identify Edison-generated command files.

        Marker-based detection is the primary mechanism. A conservative legacy
        fallback exists to prune older Edison files produced before the marker
        was added, while minimizing the risk of deleting user-authored files.
        """
        if any(marker in content for marker in self._GENERATED_MARKERS):
            return True

        if not prefix:
            # Without a prefix, legacy heuristics are too risky (e.g. `# ` matches many files).
            return False

        # Legacy Claude-style: YAML frontmatter with a `description:` plus an Edison-prefixed title.
        stripped = content.lstrip()
        if stripped.startswith("---") and "description:" in content and f"# {prefix}" in content:
            return True

        # Legacy Cursor-style: Edison-prefixed title plus common Edison sections.
        if f"# {prefix}" in content and ("## Related" in content or "## Related Commands" in content):
            return True

        return False

    def compose_all(self) -> dict[str, dict[str, Path]]:
        """Compose commands for all configured platforms."""
        definitions = self.filter_definitions(self.load_definitions())
        platforms = self._platforms()

        results: dict[str, dict[str, Path]] = {}
        for platform in platforms:
            results[platform] = self.compose_for_platform(platform, definitions)
        return results

    # ----- Helpers -----
    def _iter_definition_files(self) -> list[Path]:
        roots: list[Path] = []

        core = self.core_dir / "commands"
        if core.is_dir():
            roots.append(core)

        active = list(self.active_packs or [])
        for packs_dir in (self.bundled_packs_dir, self.user_packs_dir, self.project_packs_dir):
            for pack in active:
                p = packs_dir / str(pack) / "commands"
                if p.is_dir():
                    roots.append(p)

        for overlay in (self.user_dir / "commands", self.project_dir / "commands"):
            if overlay.is_dir():
                roots.append(overlay)

        files: list[Path] = []
        for root in roots:
            files.extend([p for p in root.glob("**/*.md") if p.is_file()])
        return files

    def _parse_definition_file(self, path: Path) -> CommandDefinition | None:
        from edison.core.utils.text import parse_frontmatter

        raw = path.read_text(encoding="utf-8")
        doc = parse_frontmatter(raw)
        meta = doc.frontmatter or {}
        cmd_id = str(meta.get("id") or "").strip()
        if not cmd_id:
            return None

        args: list[CommandArg] = []
        raw_args = meta.get("args") or []
        if isinstance(raw_args, list):
            for item in raw_args:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                args.append(
                    CommandArg(
                        name=name,
                        description=str(item.get("description") or "").strip(),
                        required=bool(item.get("required", True)),
                    )
                )

        related: list[str] = []
        raw_related = meta.get("related_commands") or meta.get("related") or []
        if isinstance(raw_related, list):
            related = [str(x) for x in raw_related if str(x).strip()]

        when_to_use = meta.get("when_to_use") or meta.get("whenToUse") or ""
        full_desc = self._render_prompt_body(str(doc.content or ""), path)

        return CommandDefinition(
            id=cmd_id,
            domain=str(meta.get("domain") or "").strip(),
            command=str(meta.get("command") or "").strip(),
            short_desc=str(meta.get("short_desc") or meta.get("shortDesc") or "").strip(),
            full_desc=full_desc.strip(),
            cli=str(meta.get("cli") or "").strip(),
            args=args,
            when_to_use=str(when_to_use).rstrip(),
            related_commands=related,
        )

    def _render_prompt_body(self, body: str, source_path: Path) -> str:
        if not body:
            return ""
        if "{{include" not in body and "{{include-section" not in body and "{{include-if" not in body and "{{if:" not in body:
            return body

        from edison.core.composition.engine import TemplateEngine
        from edison.core.composition.includes import ComposedIncludeProvider
        from edison.core.composition.registries._types_manager import ComposableTypesManager

        include_provider = ComposedIncludeProvider(
            types_manager=ComposableTypesManager(project_root=self.project_root),
            packs=tuple(self.active_packs or []),
            materialize=False,
        ).build()

        engine = TemplateEngine(
            config=self.config,
            packs=list(self.active_packs or []),
            project_root=self.project_root,
            source_dir=source_path.parent,
            include_provider=include_provider,
            strip_section_markers=True,
        )
        composed, _report = engine.process(body, entity_name=str(source_path), entity_type="commands")

        if "<!-- ERROR:" in composed:
            snippet = composed.split("<!-- ERROR:", 1)[1]
            first_line = snippet.split("-->", 1)[0].strip()
            raise RuntimeError(f"Command include resolution failed: {first_line}")

        return composed

    def _output_dir_for(self, platform: str, *, override: Path | None = None) -> Path:
        if override is not None:
            return Path(override)

        platform_cfg = self._platform_cfg(platform)
        out = platform_cfg.get("output_dir")
        if out:
            p = Path(str(out)).expanduser()
            if not p.is_absolute():
                p = (self.project_root / p).resolve()
            return Path(str(p))

        # Conservative defaults (repo-local) when no config is available.
        if platform == "claude":
            return self.project_root / ".claude" / "commands"
        if platform == "cursor":
            return self.project_root / ".cursor" / "commands"
        if platform == "codex":
            return self.project_root / ".codex" / "prompts"
        return self.project_root / "_commands" / platform

    def _platforms(self) -> list[str]:
        if not self._enabled():
            return []

        commands_cfg = self._commands_cfg()
        platforms = commands_cfg.get("platforms")
        if isinstance(platforms, list) and platforms:
            raw = [str(p).lower() for p in platforms]
        else:
            raw = ["claude", "cursor", "codex"]

        # Filter out explicitly disabled platform configs
        out: list[str] = []
        for p in raw:
            if self._platform_cfg(p).get("enabled") is False:
                continue
            out.append(p)
        return out

    def _enabled(self) -> bool:
        commands_cfg = self._commands_cfg()
        return commands_cfg.get("enabled") is not False

    def _commands_cfg(self) -> dict[str, Any]:
        return (self.config or {}).get("commands", {}) or {}

    def _platform_cfg(self, platform: str) -> dict[str, Any]:
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
    def _normalize_related_commands(related: list[str], *, prefix: str) -> list[str]:
        out: list[str] = []
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
        candidates: list[Path] = []

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
    config: dict[str, Any],
    platforms: list[str] | None = None,
    repo_root: Path | None = None,
) -> dict[str, dict[str, Path]]:
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

        def sync_all(self) -> dict[str, Any]:
            return {}

    root = (repo_root or Path.cwd()).resolve()
    adapter = _ComposeCommandsAdapter(project_root=root)
    adapter.config = adapter.cfg_mgr.deep_merge(adapter.config, config)
    composer = CommandComposer(adapter.context)
    definitions = composer.filter_definitions(composer.load_definitions())

    target_platforms: list[str]
    if platforms is None:
        target_platforms = composer._platforms()
    else:
        target_platforms = [p.lower() for p in platforms]

    results: dict[str, dict[str, Path]] = {}
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
