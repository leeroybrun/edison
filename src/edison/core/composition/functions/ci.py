"""
CI command helpers for template composition.

These functions are available to templates via {{function:...}} and are designed
to keep core guidance technology-agnostic while allowing projects/packs to
surface their configured commands in prompts and guidelines.
"""
from __future__ import annotations

import json
from typing import Optional

from edison.core.composition.transformers.base import TransformContext


def _config_or(ctx: TransformContext, path: str, fallback: str = "") -> str:
    """Return config value for ``path`` or ``fallback`` when missing/blank."""
    value = ctx.get_config(path)
    if value is None:
        return fallback
    rendered = str(value).strip()
    return rendered if rendered else fallback


def _looks_like_placeholder(value: str) -> bool:
    v = (value or "").strip()
    return bool(v) and v.startswith("<") and v.endswith(">")


def _detect_package_manager(ctx: TransformContext) -> str | None:
    root = ctx.project_root
    if root is None:
        return None
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return None
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    pm_raw = data.get("packageManager")
    if not isinstance(pm_raw, str) or "@" not in pm_raw:
        return None
    name = pm_raw.split("@", 1)[0].strip().lower()
    return name if name in {"pnpm", "npm", "yarn", "bun"} else None


def _detect_script(ctx: TransformContext, name: str) -> str | None:
    root = ctx.project_root
    if root is None:
        return None
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return None
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return None

    candidates: list[str]
    if name == "type-check":
        candidates = ["type-check", "typecheck"]
    elif name == "format-check":
        candidates = ["format:check", "format-check", "fmt:check", "fmt-check", "check-format"]
    elif name == "test-coverage":
        candidates = ["test:coverage", "coverage", "test-coverage"]
    elif name == "format":
        candidates = ["format", "fmt"]
    else:
        candidates = [name]

    for cand in candidates:
        if cand in scripts and isinstance(scripts.get(cand), str) and str(scripts.get(cand)).strip():
            return cand
    return None


def _command_for_script(pm: str, script: str) -> str:
    if pm == "npm":
        return f"npm run {script}"
    return f"{pm} {script}"


def ci_command(ctx: TransformContext, name: str, fallback: Optional[str] = None) -> str:
    """Return the configured CI command for ``name`` (e.g. lint/test/build).

    Reads ``ci.commands.<name>`` from merged config. If the value is missing or
    blank, falls back to ``project.commands.<name>`` (legacy/general shortcut).
    If still missing, returns ``fallback``; if fallback is not provided, uses a
    reasonable placeholder string.
    """
    fallback_value = fallback if fallback is not None else f"<{name}-command>"
    primary = _config_or(ctx, f"ci.commands.{name}", "")
    if primary and not _looks_like_placeholder(primary):
        # Heuristic: if the project declares a different package manager,
        # prefer script-based invocation over "npm run ..." defaults.
        pm = _detect_package_manager(ctx)
        script = _detect_script(ctx, name)
        if pm and script and pm != "npm" and primary.startswith("npm "):
            return _command_for_script(pm, script)
        return primary

    pm = _detect_package_manager(ctx)
    script = _detect_script(ctx, name)
    if pm and script:
        return _command_for_script(pm, script)

    secondary = _config_or(ctx, f"project.commands.{name}", "")
    return secondary if secondary else fallback_value
