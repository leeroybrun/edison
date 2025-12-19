"""
CI command helpers for template composition.

These functions are available to templates via {{function:...}} and are designed
to keep core guidance technology-agnostic while allowing projects/packs to
surface their configured commands in prompts and guidelines.
"""
from __future__ import annotations

from typing import Optional

from edison.core.composition.transformers.base import TransformContext


def _config_or(ctx: TransformContext, path: str, fallback: str = "") -> str:
    """Return config value for ``path`` or ``fallback`` when missing/blank."""
    value = ctx.get_config(path)
    if value is None:
        return fallback
    rendered = str(value).strip()
    return rendered if rendered else fallback


def ci_command(ctx: TransformContext, name: str, fallback: Optional[str] = None) -> str:
    """Return the configured CI command for ``name`` (e.g. lint/test/build).

    Reads ``ci.commands.<name>`` from merged config. If the value is missing or
    blank, falls back to ``project.commands.<name>`` (legacy/general shortcut).
    If still missing, returns ``fallback``; if fallback is not provided, uses a
    reasonable placeholder string.
    """
    fallback_value = fallback if fallback is not None else f"<{name}-command>"
    primary = _config_or(ctx, f"ci.commands.{name}", "")
    if primary:
        return primary
    secondary = _config_or(ctx, f"project.commands.{name}", "")
    return secondary if secondary else fallback_value
