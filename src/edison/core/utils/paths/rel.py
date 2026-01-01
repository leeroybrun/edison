"""Relative path helpers.

Centralizes common "best-effort relative to project root" formatting so
domain code avoids duplicating subtle Path.resolve/relative_to handling.
"""

from __future__ import annotations

from pathlib import Path


def safe_relpath(path: Path, *, project_root: Path) -> str:
    """Return a best-effort project-root-relative path string."""
    try:
        return str(Path(path).resolve().relative_to(Path(project_root).resolve()))
    except Exception:
        return str(path)


__all__ = ["safe_relpath"]

