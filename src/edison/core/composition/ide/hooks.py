#!/usr/bin/env python3
from __future__ import annotations

"""Compose Claude Code hooks from Edison configuration."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Optional dependency; fall back to plain text rendering when absent
    from jinja2 import Template  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    Template = None  # type: ignore[assignment]

from edison.core.utils.io import ensure_directory
from edison.data import get_data_path
from .base import IDEComposerBase


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
    matcher: Optional[str] = None
    description: str = ""
    template: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


class HookComposer(IDEComposerBase):
    """Generate Claude Code hook scripts based on merged configuration."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        super().__init__(config=config, repo_root=repo_root)
        # Use bundled Edison data for templates (not project's core_dir)
        self.templates_dir = get_data_path("templates", "hooks")
        # Bundled Edison config directory
        self._bundled_config_dir = get_data_path("config")

    # ----- Public API -----
    def load_definitions(self) -> Dict[str, HookDefinition]:
        """Load and merge hook definitions from core, packs, and project overrides.

        Uses unified _load_layered_config() from CompositionBase to load from:
        1. Core: bundled edison.data/config/hooks.yaml
        2. Packs: edison.data/packs/{pack}/config/hooks.yaml
        3. Project: .edison/config/hooks.yml
        """
        # Use unified layered config loading
        data = self._load_layered_config("hooks", subdirs=["config"])

        # Extract definitions from the loaded data
        merged = self._extract_hook_definitions(data)

        return self._dicts_to_defs(merged)

    def render_hook(self, hook_def: HookDefinition) -> str:
        """Render a single hook using its template (Jinja2 when available)."""
        hooks_cfg = self._hooks_cfg()
        template_path = self._resolve_template(hook_def.template)
        return self._render_template(template_path, hook_def, hooks_cfg)

    def compose_hooks(self) -> Dict[str, Path]:
        """Render and write enabled hooks for Claude Code."""
        hooks_cfg = self._hooks_cfg()
        # Default to enabled; only skip when explicitly disabled.
        if hooks_cfg.get("enabled") is False:
            return {}

        platforms = [str(p).lower() for p in hooks_cfg.get("platforms") or ["claude"]]
        if "claude" not in platforms:
            return {}

        output_dir = ensure_directory(self._output_dir(hooks_cfg))

        definitions = self.load_definitions()
        results: Dict[str, Path] = {}
        for hook_id, hook_def in definitions.items():
            if not hook_def.enabled:
                continue

            rendered = self.render_hook(hook_def)

            outfile = self._output_filename(hook_def)
            out_path = output_dir / outfile
            written_path = self.writer.write_executable(out_path, rendered)
            results[hook_id] = written_path

        return results

    def generate_settings_json_hooks_section(self) -> Dict[str, List[Dict[str, Any]]]:
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

        scripts = self.compose_hooks()
        definitions = self.load_definitions()

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for hook_id, hook_def in definitions.items():
            if not hook_def.enabled or hook_id not in scripts:
                continue

            entry: Dict[str, Any] = {"hooks": []}

            # Only add matcher for tool-based events
            if hook_def.type not in NON_TOOL_EVENTS:
                entry["matcher"] = hook_def.matcher or "*"

            path_str = str(scripts[hook_id])
            # Shell scripts always use type: command
            # (Edison's hook_type: prompt meant stdout injection, but Claude Code
            # handles that automatically for UserPromptSubmit command hooks)
            entry["hooks"].append({"type": "command", "command": path_str})

            grouped.setdefault(hook_def.type, []).append(entry)

        return grouped

    # ----- Helpers -----
    def _hooks_cfg(self) -> Dict:
        return (self.config or {}).get("hooks", {}) or {}

    def _extract_hook_definitions(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract hook definitions from loaded layered config data.

        Args:
            data: Merged config data from _load_layered_config()

        Returns:
            Dict of hook definitions keyed by hook id
        """
        if not isinstance(data, dict):
            return {}

        hooks = data.get("hooks")
        if isinstance(hooks, dict):
            defs = hooks.get("definitions")
            if isinstance(defs, dict):
                return defs

        return {}

    def _dicts_to_defs(self, merged: Dict[str, Dict[str, Any]]) -> Dict[str, HookDefinition]:
        """Convert merged dicts into HookDefinition objects with validation."""
        results: Dict[str, HookDefinition] = {}
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

    def _output_dir(self, hooks_cfg: Dict) -> Path:
        override = hooks_cfg.get("output_dir")
        if override:
            return Path(str(Path(str(override)).expanduser()))
        return self.repo_root / ".claude" / "hooks"

    def _resolve_template(self, name: str) -> Optional[Path]:
        if not name:
            return None

        # Priority: project templates > pack templates > bundled Edison templates
        # Build list of candidates in priority order
        candidates = [
            self.project_dir / "templates" / "hooks" / name,
        ]

        # Add pack templates in reverse order (later packs override earlier ones)
        # So we check in forward order: last pack's template wins
        for pack in reversed(self._active_packs()):
            # Check bundled pack templates first
            candidates.append(self.bundled_packs_dir / pack / "templates" / "hooks" / name)
            # Also check project-level pack templates (for user overrides)
            candidates.append(self.project_packs_dir / pack / "templates" / "hooks" / name)

        # Finally, bundled Edison core templates
        candidates.append(self.templates_dir / name)

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _render_template(
        self,
        template_path: Optional[Path],
        hook_def: HookDefinition,
        hooks_cfg: Dict,
    ) -> str:
        context = {
            "id": hook_def.id,
            "hook": hook_def,
            "config": hook_def.config,
            "description": hook_def.description,
            "type": hook_def.type,
            "hook_type": hook_def.hook_type,
            "blocking": hook_def.blocking,
            "matcher": hook_def.matcher,
            "settings": hooks_cfg.get("settings", {}),
        }

        if template_path and template_path.exists():
            raw = template_path.read_text(encoding="utf-8")
            # Check if template uses Jinja2 block tags that require full Jinja2
            if Template is None and self._uses_jinja2_block_tags(raw):
                raise RuntimeError(
                    f"Template '{template_path.name}' uses Jinja2 block tags "
                    f"({{% set %}}, {{% if %}}, {{% for %}}, etc.) but Jinja2 is not installed. "
                    f"Install Jinja2 with: pip install Jinja2>=3.0"
                )
            if Template is None:
                return self._render_basic_template(raw, context)
            template = Template(template_path.read_text(encoding="utf-8"))
            return template.render(**context)

        raise ValueError(f"Template not found for hook: {hook_def.id}")

    def _uses_jinja2_block_tags(self, text: str) -> bool:
        """Check if template text contains Jinja2 block tags that require full Jinja2."""
        # Match {% ... %} block tags (set, if, for, endif, endfor, else, elif, etc.)
        return bool(re.search(r"{%\s*\w+", text))

    def _render_basic_template(self, text: str, context: Dict) -> str:
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


def compose_hooks(config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> Dict[str, Path]:
    """Module-level convenience wrapper to compose hooks."""
    return HookComposer(config=config, repo_root=repo_root).compose_hooks()


__all__ = ["HookComposer", "HookDefinition", "compose_hooks", "ALLOWED_TYPES"]



