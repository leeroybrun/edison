"""NO-LEGACY guard helpers for Edison core libraries.

These helpers provide a lightweight, import-time check to ensure that
Edison core modules are never executed against pre-Edison repositories
such as ``project-pre-edison``.

The intent is to fail fast with a clear error message whenever the
resolved project root points at a legacy tree, enforcing the policy
defined in ``.project/qa/EDISON_NO_LEGACY_POLICY.md``.
"""
from __future__ import annotations

from pathlib import Path

from .paths import PathResolver, EdisonPathError


LEGACY_ROOT_MARKERS = ("project-pre-edison",)


def _is_legacy_root(root: Path) -> bool:
    text = str(root)
    return any(marker in text for marker in LEGACY_ROOT_MARKERS)


def enforce_no_legacy_project_root(module_name: str) -> None:
    """Fail fast if the resolved project root is a legacy pre-Edison tree.

    Args:
        module_name: Human-readable module identifier for error messages.

    Raises:
        RuntimeError: When the resolved project root path contains a known
            legacy marker such as ``project-pre-edison``.
    """
    try:
        root = PathResolver.resolve_project_root()
    except EdisonPathError:
        # When the project root cannot be resolved, do not add additional
        # failure modes here; callers will surface the underlying error.
        return

    if _is_legacy_root(root):
        raise RuntimeError(
            f"NO-LEGACY violation: {module_name} detected legacy pre-Edison project root {root}. "
            "Set AGENTS_PROJECT_ROOT to the new Edison-enabled repository and remove pre-Edison paths from active workflows."
        )


__all__ = ["enforce_no_legacy_project_root"]
