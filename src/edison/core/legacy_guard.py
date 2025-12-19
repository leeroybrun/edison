"""NO-LEGACY guard helpers for Edison core libraries.

These helpers provide a lightweight, import-time check to ensure that
Edison core modules are never executed against pre-Edison repositories
such as ``project-pre-edison``.

The intent is to fail fast with a clear error message whenever the
resolved project root points at a legacy tree, enforcing the policy
defined in ``<project-management-dir>/qa/EDISON_NO_LEGACY_POLICY.md``.
"""
from __future__ import annotations

import os
from pathlib import Path

LEGACY_ROOT_MARKERS = ("project-pre-edison",)


def _is_legacy_root(root: Path) -> bool:
    text = str(root)
    return any(marker in text for marker in LEGACY_ROOT_MARKERS)


def _resolve_project_root_lightweight() -> Path | None:
    """Lightweight project root resolution without importing PathResolver.
    
    This avoids circular imports when called at module load time.
    Returns None if project root cannot be determined.
    """
    # Check environment variable first (most common case)
    env_root = os.environ.get("AGENTS_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    
    # Fall back to cwd-based detection
    cwd = Path.cwd()
    
    # Look for project management directories as markers
    project_config_dir_name = (
        os.environ.get("EDISON_paths__project_config_dir")
        or os.environ.get("EDISON_paths__config_dir")
        or ".edison"
    )
    project_management_dir_name = (
        os.environ.get("EDISON_project_management_dir")
        or os.environ.get("EDISON_paths__management_dir")
        or ".project"
    )
    for parent in [cwd, *cwd.parents]:
        if (parent / project_config_dir_name).exists() or (parent / project_management_dir_name).exists():
            return parent
    
    return None


def enforce_no_legacy_project_root(module_name: str) -> None:
    """Fail fast if the resolved project root is a legacy pre-Edison tree.

    Args:
        module_name: Human-readable module identifier for error messages.

    Raises:
        RuntimeError: When the resolved project root path contains a known
            legacy marker such as ``project-pre-edison``.
    """
    root = _resolve_project_root_lightweight()
    
    if root is None:
        # Cannot determine project root - don't add failure modes
        return

    if _is_legacy_root(root):
        raise RuntimeError(
            f"NO-LEGACY violation: {module_name} detected legacy pre-Edison project root {root}. "
            "Set AGENTS_PROJECT_ROOT to the new Edison-enabled repository and remove pre-Edison paths from active workflows."
        )


__all__ = ["enforce_no_legacy_project_root"]
