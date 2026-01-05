"""Evidence helpers for template composition.

These helpers are used in composed guidance prompts and must remain stable.
Validation requirements are preset-driven; when template rendering has no task
context, we treat the `standard` preset as the canonical baseline.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from edison.core.composition.transformers.base import TransformContext


_DEFAULT_EVIDENCE_FILES_BY_NAME = {
    "type-check": "command-type-check.txt",
    "lint": "command-lint.txt",
    "test": "command-test.txt",
    "build": "command-build.txt",
}


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def required_evidence_files(ctx: TransformContext, fmt: str = "inline") -> str:
    """Render required evidence files from config.

    Reads ``validation.evidence.requiredFiles`` (baseline). If missing, falls back to
    core defaults for type-check/lint/test/build.

    Args:
        fmt: One of:
          - "inline": backticked list, comma-separated
          - "bullets": markdown bullets, each backticked
          - "plain": comma-separated without backticks
    """
    files = _as_list(ctx.get_config("validation.evidence.requiredFiles"))
    if not files:
        files = list(_DEFAULT_EVIDENCE_FILES_BY_NAME.values())

    if fmt == "bullets":
        return "\n".join(f"- `{f}`" for f in files)
    if fmt == "plain":
        return ", ".join(files)
    # inline (default)
    return ", ".join(f"`{f}`" for f in files)


def evidence_file(ctx: TransformContext, name: str) -> str:
    """Return the configured evidence filename for a logical command name.

    Reads ``validation.evidence.files.<name>``. If missing/blank, falls back to
    core defaults for the common names (type-check/lint/test/build); otherwise
    falls back to ``command-<name>.txt``.
    """
    key = str(name).strip()
    if not key:
        return "command-evidence.txt"

    configured = ctx.get_config(f"validation.evidence.files.{key}")
    if configured is not None:
        rendered = str(configured).strip()
        if rendered:
            return rendered

    if key in _DEFAULT_EVIDENCE_FILES_BY_NAME:
        return _DEFAULT_EVIDENCE_FILES_BY_NAME[key]

    return f"command-{key}.txt"
