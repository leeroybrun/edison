"""Compose Claude Code hooks from Edison configuration.

This module generates hook scripts for Claude Code based on merged
configuration from core, packs, user, and project layers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # Optional dependency; fall back to plain text rendering when absent
    from jinja2 import Environment
except Exception:  # pragma: no cover - handled at runtime
    Environment = None  # type: ignore[misc, assignment]

from edison.core.config import ConfigManager
from edison.core.utils.io import ensure_directory
from edison.data import get_data_path

from .base import AdapterComponent, AdapterContext

# Allowed hook lifecycle event types (kept in sync with tests)
ALLOWED_TYPES = [
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "PreCompact",
    "Stop",
    "SubagentStop",
]


@dataclass
class HookDefinition:
    """Declarative hook definition used for rendering."""

    id: str
    type: str
    hook_type: str = "command"
    enabled: bool = True
    blocking: bool = False
    matcher: str | None = None
    description: str = ""
    template: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    execution_scope: str = "session"  # "session" | "project" | "always"


class HookComposer(AdapterComponent):
    """Generate hook scripts based on merged configuration (platform-agnostic)."""

    def __init__(self, context: AdapterContext) -> None:
        super().__init__(context)

        # Use bundled Edison data for templates (not project's core_dir)
        self.templates_dir = Path(get_data_path("templates", "hooks"))
        self._bundled_config_dir = Path(get_data_path("config"))

    # ----- Public API -----
    def compose(self) -> dict[str, HookDefinition]:
        """Return merged hook definitions (core → packs → user → project)."""
        return self.load_definitions()

    def sync(self, output_dir: Path) -> list[Path]:
        """Render and write hooks to ``output_dir``.

        This is a thin wrapper around ``compose_hooks`` to satisfy the
        AdapterComponent contract.
        """
        written = self.compose_hooks(output_dir_override=output_dir)
        return list(written.values())

    def load_definitions(self) -> dict[str, HookDefinition]:
        """Load and merge hook definitions using ConfigManager's pack-aware loading.

        ConfigManager handles the full layering:
        1. Core config (bundled hooks.yaml)
        2. Pack configs (bundled + user + project packs)
        3. User config (~/.edison/config/hooks.yaml)
        4. Project config (.edison/config/hooks.yaml)
        5. Project-local config (.edison/config.local/hooks.yaml)
        """

        cfg_mgr = ConfigManager(repo_root=self.project_root)
        full_config = cfg_mgr.load_config(validate=False, include_packs=True)

        hooks_section = full_config.get("hooks", {}) or {}
        definitions = hooks_section.get("definitions", {}) or {}

        return self._dicts_to_defs(definitions)

    def render_hook(self, hook_def: HookDefinition) -> str:
        """Render a single hook using its template (Jinja2 when available)."""
        hooks_cfg = self._hooks_cfg()
        template_path = self._resolve_template(hook_def.template)
        return self._render_template(template_path, hook_def, hooks_cfg)

    def compose_hooks(self, *, output_dir_override: Path | None = None) -> dict[str, Path]:
        """Render and write enabled hooks for Claude Code.

        Args:
            output_dir_override: Optional directory override for this run.
                When provided, hooks are written under this directory and any
                generated settings.json hook paths should reference it.
        """
        hooks_cfg = self._hooks_cfg()
        if output_dir_override is not None:
            hooks_cfg["output_dir_override"] = str(output_dir_override)
        # Default to enabled; only skip when explicitly disabled.
        if hooks_cfg.get("enabled") is False:
            return {}

        platforms = [str(p).lower() for p in hooks_cfg.get("platforms") or ["claude"]]
        if "claude" not in platforms:
            return {}

        output_dir = ensure_directory(self._output_dir(hooks_cfg))

        # Generate shared guard script first
        self._generate_guard_script(output_dir)

        definitions = self.load_definitions()
        results: dict[str, Path] = {}
        for hook_id, hook_def in definitions.items():
            if not hook_def.enabled:
                continue

            rendered = self.render_hook(hook_def)

            outfile = self._output_filename(hook_def)
            out_path = output_dir / outfile
            ensure_directory(out_path.parent)
            out_path.write_text(rendered, encoding="utf-8")
            # Ensure executable bit for hook scripts
            out_path.chmod(out_path.stat().st_mode | 0o111)
            results[hook_id] = out_path

        return results

    def _generate_guard_script(self, output_dir: Path) -> Path:
        """Generate the shared guard script (_edison_guard.sh).

        The guard script provides a unified `edison_hook_guard` function that:
        - Checks for Edison session using `edison session detect`
        - Exits early (0) if executionScope=session and no session detected
        - Continues if executionScope=project or executionScope=always
        """
        guard_template = self.templates_dir / "_edison_guard.sh.template"
        if not guard_template.exists():
            raise FileNotFoundError(f"Guard template not found at {guard_template}")

        raw = guard_template.read_text(encoding="utf-8")

        # Render template (simple variable expansion, no hook-specific context)
        if Environment is not None:
            env = Environment(trim_blocks=True, lstrip_blocks=True)
            rendered = env.from_string(raw).render()
        else:
            rendered = raw

        guard_path = output_dir / "_edison_guard.sh"
        guard_path.write_text(rendered, encoding="utf-8")
        guard_path.chmod(guard_path.stat().st_mode | 0o111)
        return guard_path

    def generate_settings_json_hooks_section(
        self, *, output_dir_override: Path | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Summarize hooks for inclusion in settings.json.

        Returns the hooks grouped by lifecycle event type (e.g., PreToolUse, PostToolUse).
        The caller should assign this directly to settings["hooks"].

        Claude Code hook format:
        - Tool events (PreToolUse, PostToolUse) use "matcher" to filter by tool name
        - Non-tool events (UserPromptSubmit, SessionStart, SessionEnd, Stop, SubagentStop)
          should NOT have a "matcher" field
        - Shell scripts always use type: "command" with a "command" field
        - type: "prompt" is for LLM evaluation prompts (text), not shell scripts
        """
        # Events that don't use tool matchers
        NON_TOOL_EVENTS = {"UserPromptSubmit", "SessionStart", "SessionEnd", "Stop", "SubagentStop", "PreCompact"}

        scripts = self.compose_hooks(output_dir_override=output_dir_override)
        definitions = self.load_definitions()

        grouped: dict[str, list[dict[str, Any]]] = {}
        for hook_id, hook_def in definitions.items():
            if not hook_def.enabled or hook_id not in scripts:
                continue

            entry: dict[str, Any] = {"hooks": []}

            # Only add matcher for tool-based events
            if hook_def.type not in NON_TOOL_EVENTS:
                entry["matcher"] = hook_def.matcher or "*"

            path_str = str(scripts[hook_id])
            # Shell scripts always use type: command
            entry["hooks"].append({"type": "command", "command": path_str})

            grouped.setdefault(hook_def.type, []).append(entry)

        return grouped

    # ----- Helpers -----
    def _hooks_cfg(self) -> dict[str, Any]:
        return (self.config or {}).get("hooks", {}) or {}


    def _dicts_to_defs(self, merged: dict[str, dict[str, Any]]) -> dict[str, HookDefinition]:
        """Convert merged dicts into HookDefinition objects with validation."""
        results: dict[str, HookDefinition] = {}
        for hook_id, raw in merged.items():
            hook_type = str(raw.get("type") or "Hook")
            if hook_type not in ALLOWED_TYPES:
                raise ValueError(f"Unsupported hook type: {hook_type}")
            blocking = bool(raw.get("blocking", False))
            if blocking and hook_type != "PreToolUse":
                raise ValueError("blocking hooks only allowed for PreToolUse")
            cfg = raw.get("config") if isinstance(raw.get("config"), dict) else {}
            cfg = self._normalize_override_lists(cfg)
            defn = HookDefinition(
                id=hook_id,
                type=hook_type,
                hook_type=str(raw.get("hook_type") or "command"),
                enabled=bool(raw.get("enabled", True)),
                blocking=blocking,
                matcher=raw.get("matcher"),
                description=str(raw.get("description", "")),
                template=str(raw.get("template", "") or ""),
                config=cfg,
                execution_scope=str(raw.get("executionScope", "session")),
            )
            results[hook_id] = defn
        return results

    def _normalize_override_lists(self, obj: Any) -> Any:
        """Strip '=' prefixes used to signal replacement in override lists."""
        if isinstance(obj, list):
            return [self._normalize_override_lists(self._strip_override_token(item)) for item in obj]
        if isinstance(obj, dict):
            return {k: self._normalize_override_lists(v) for k, v in obj.items()}
        return obj

    @staticmethod
    def _strip_override_token(item: Any) -> Any:
        if isinstance(item, str) and item.startswith("="):
            return item[1:]
        return item

    def _output_dir(self, hooks_cfg: dict[str, Any]) -> Path:
        # Explicit override (e.g., from sync(output_dir))
        override = hooks_cfg.get("output_dir_override") or hooks_cfg.get("output_dir")
        if override:
            return Path(str(Path(str(override)).expanduser()))
        return self.project_root / ".claude" / "hooks"

    def _resolve_template(self, name: str) -> Path | None:
        if not name:
            return None

        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(self.project_root)

        candidates: list[Path] = []
        for _layer_id, layer_root in reversed(resolver.overlay_layers):
            candidates.append(layer_root / "templates" / "hooks" / name)

        # Add pack templates in reverse order (later packs override earlier ones).
        # Within a given pack name, precedence is highest pack root first.
        for pack in reversed(self.active_packs):
            for root in reversed(resolver.pack_roots):
                candidates.append(root.path / pack / "templates" / "hooks" / name)

        # Finally, bundled Edison core templates
        candidates.append(self.templates_dir / name)

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _render_template(
        self,
        template_path: Path | None,
        hook_def: HookDefinition,
        hooks_cfg: dict[str, Any],
    ) -> str:
        context = {
            "id": hook_def.id,
            "hook": hook_def,
            "config": hook_def.config,
            "global_config": self.config,
            "description": hook_def.description,
            "type": hook_def.type,
            "hook_type": hook_def.hook_type,
            "blocking": hook_def.blocking,
            "matcher": hook_def.matcher,
            "settings": hooks_cfg.get("settings", {}),
            "execution_scope": hook_def.execution_scope,
        }

        if template_path and template_path.exists():
            raw = template_path.read_text(encoding="utf-8")
            # Check if template uses Jinja2 block tags that require full Jinja2
            if Environment is None and self._uses_jinja2_block_tags(raw):
                raise RuntimeError(
                    f"Template '{template_path.name}' uses Jinja2 block tags "
                    f"({{% set %}}, {{% if %}}, {{% for %}}, etc.) but Jinja2 is not installed. "
                    f"Install Jinja2 with: pip install Jinja2>=3.0"
                )
            if Environment is None:
                return self._render_basic_template(raw, context)
            # The bundled hook templates frequently use control blocks on their own lines.
            # Without trimming, those lines become empty lines in the rendered scripts.
            env = Environment(trim_blocks=True, lstrip_blocks=True)
            template = env.from_string(raw)
            return template.render(**context)

        raise ValueError(f"Template not found for hook: {hook_def.id}")

    def _uses_jinja2_block_tags(self, text: str) -> bool:
        """Check if template text contains Jinja2 block tags that require full Jinja2."""
        return bool(re.search(r"{%\s*\w+", text))

    def _render_basic_template(self, text: str, context: dict[str, Any]) -> str:
        """Very small placeholder renderer for when Jinja2 is unavailable."""

        def _lookup(expr: str) -> str:
            cur: object = context
            for part in expr.split("."):
                if isinstance(cur, dict):
                    cur = cur.get(part, "")
                else:
                    return ""
            try:
                return str(cur)
            except Exception:
                return ""

        return re.sub(r"{{\s*(.*?)\s*}}", lambda m: _lookup(m.group(1)), text)

    def _output_filename(self, hook_def: HookDefinition) -> str:
        """Derive output file name from the template while keeping hook id."""
        if hook_def.template:
            suffixes = Path(hook_def.template).suffixes
            if suffixes and suffixes[-1] == ".template":
                suffix = "".join(suffixes[:-1]) or ".hook"
            else:
                suffix = "".join(suffixes) or ".hook"
            return f"{hook_def.id}{suffix}"
        return f"{hook_def.id}.hook"


def compose_hooks(
    config: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> dict[str, Path]:
    """Module-level convenience wrapper to compose hooks.

    Prefer constructing HookComposer from a PlatformAdapter.context in new code.
    """
    from edison.core.adapters.base import PlatformAdapter

    class _ComposeHooksAdapter(PlatformAdapter):
        @property
        def platform_name(self) -> str:
            return "compose-hooks"

        def sync_all(self) -> dict[str, Any]:
            return {}

    root = (repo_root or Path.cwd()).resolve()
    adapter = _ComposeHooksAdapter(project_root=root)
    if config:
        adapter.config = adapter.cfg_mgr.deep_merge(adapter.config, config)
    composer = HookComposer(adapter.context)
    return composer.compose_hooks()


__all__ = ["HookComposer", "HookDefinition", "compose_hooks", "ALLOWED_TYPES"]
