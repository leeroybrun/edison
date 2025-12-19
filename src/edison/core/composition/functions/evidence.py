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

