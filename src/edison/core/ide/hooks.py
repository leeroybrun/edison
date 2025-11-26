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

from ..config import ConfigManager
from ..paths.project import get_project_config_dir
from ..composition.includes import _repo_root, _REPO_ROOT_OVERRIDE
from ..file_io.utils import ensure_dir


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


class HookComposer:
    """Generate Claude Code hook scripts based on merged configuration."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or _repo_root()
        global _REPO_ROOT_OVERRIDE
        _REPO_ROOT_OVERRIDE = self.repo_root

        if config is None:
            cfg_mgr = ConfigManager(self.repo_root)
            self.config = cfg_mgr.load_config(validate=False)
        else:
            self.config = config

        self.cfg_mgr = ConfigManager(self.repo_root)

        config_dir = get_project_config_dir(self.repo_root, create=False)
        self.core_dir = config_dir / "core"
        self.packs_dir = config_dir / "packs"
        self.project_dir = config_dir
        self.templates_dir = self.core_dir / "templates" / "hooks"

    # ----- Public API -----
    def load_definitions(self) -> Dict[str, HookDefinition]:
        """Load and merge hook definitions from core, packs, and project overrides."""
        merged: Dict[str, Dict[str, Any]] = {}

        core_file = self.core_dir / "config" / "hooks.yaml"
        merged = self._merge_from_file(merged, core_file)

        for pack in self._active_packs():
            pack_file = self.packs_dir / pack / "config" / "hooks.yml"
            merged = self._merge_from_file(merged, pack_file)

        project_file = self.project_dir / "config" / "hooks.yml"
        merged = self._merge_from_file(merged, project_file)

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

        output_dir = ensure_dir(self._output_dir(hooks_cfg))

        definitions = self.load_definitions()
        results: Dict[str, Path] = {}
        for hook_id, hook_def in definitions.items():
            if not hook_def.enabled:
                continue

            rendered = self.render_hook(hook_def)

            outfile = self._output_filename(hook_def)
            out_path = output_dir / outfile
            ensure_dir(out_path.parent)
            out_path.write_text(rendered, encoding="utf-8")
            # Ensure executable bit for hook scripts
            out_path.chmod(out_path.stat().st_mode | 0o111)
            results[hook_id] = out_path

        return results

    def generate_settings_json_hooks_section(self) -> Dict[str, List[Dict[str, Any]]]:
        """Summarize hooks for inclusion in settings.json.

        Returns the hooks grouped by lifecycle event type (e.g., PreToolUse, PostToolUse).
        The caller should assign this directly to settings["hooks"].
        """
        scripts = self.compose_hooks()
        definitions = self.load_definitions()

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for hook_id, hook_def in definitions.items():
            if not hook_def.enabled or hook_id not in scripts:
                continue
            entry: Dict[str, Any] = {
                "matcher": hook_def.matcher or "*",
                "hooks": [],
            }
            path_str = str(scripts[hook_id])
            if hook_def.hook_type == "prompt":
                entry["hooks"].append({"type": "prompt", "prompt": path_str})
            else:  # default to command hook
                entry["hooks"].append({"type": "command", "command": path_str})
            grouped.setdefault(hook_def.type, []).append(entry)

        return grouped

    # ----- Helpers -----
    def _hooks_cfg(self) -> Dict:
        return (self.config or {}).get("hooks", {}) or {}

    def _active_packs(self) -> List[str]:
        packs = ((self.config or {}).get("packs", {}) or {}).get("active", [])
        if not isinstance(packs, list):
            return []
        return [str(p) for p in packs]

    def _merge_from_file(self, merged: Dict[str, Dict[str, Any]], path: Path) -> Dict[str, Dict[str, Any]]:
        """Load hook definitions from ``path`` and merge into ``merged`` by id."""
        data = self._load_yaml_hooks(path)
        for hook_id, raw in data.items():
            if not isinstance(raw, dict):
                continue
            existing = merged.get(hook_id, {})
            merged[hook_id] = self.cfg_mgr.deep_merge(existing, raw)
        return merged

    def _load_yaml_hooks(self, path: Path) -> Dict[str, Dict[str, Any]]:
        """Load hook ``definitions`` mapping from YAML path (empty when missing)."""
        data = self.cfg_mgr.load_yaml(path)
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

        candidates = [
            self.project_dir / "templates" / "hooks" / name,
            self.core_dir / "templates" / "hooks" / name,
        ]
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
            if Template is None:
                raw = template_path.read_text(encoding="utf-8")
                return self._render_basic_template(raw, context)
            template = Template(template_path.read_text(encoding="utf-8"))
            return template.render(**context)

        # Fallback plain script when no template is available
        lines = [
            "#!/usr/bin/env bash",
            f"# Hook: {hook_def.id}",
            f"# Description: {hook_def.description}",
            "",
            "exit 0",
        ]
        return "\n".join(lines).rstrip() + "\n"

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


__all__ = ["HookComposer", "HookDefinition", "compose_hooks"]


def compose_hooks(config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> Dict[str, Path]:
    """Module-level convenience wrapper to compose hooks."""
    return HookComposer(config=config, repo_root=repo_root).compose_hooks()
