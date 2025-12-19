"""Evidence helpers for template composition."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from edison.core.composition.transformers.base import TransformContext


_DEFAULT_REQUIRED_EVIDENCE_FILES = [
    "command-type-check.txt",
    "command-lint.txt",
    "command-test.txt",
    "command-build.txt",
]

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

    Reads ``validation.requiredEvidenceFiles``. Falls back to core defaults when
    missing to avoid unresolved template markers in downstream guides.

    Args:
        fmt: One of:
          - "inline": backticked list, comma-separated
          - "bullets": markdown bullets, each backticked
          - "plain": comma-separated without backticks
    """
    configured = _as_list(ctx.get_config("validation.requiredEvidenceFiles"))
    files = configured or list(_DEFAULT_REQUIRED_EVIDENCE_FILES)

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
