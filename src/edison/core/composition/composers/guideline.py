#!/usr/bin/env python3
from __future__ import annotations

"""Guideline composition utilities."""

from pathlib import Path
from typing import Dict, Iterable, Optional


def compose_guidelines(
    active_packs: Iterable[str],
    project_config: Optional[Dict] = None,
    *,
    repo_root: Optional[Path] = None,
    names: Optional[Iterable[str]] = None,
    project_overrides: bool = True,
    dry_min_shingles: Optional[int] = None,
) -> Dict[str, Path]:
    """Compose guidelines from core, packs, and project overlays.

    This is a standalone function that wraps CompositionEngine for backward compatibility.

    Args:
        active_packs: List of active pack names
        project_config: Optional project configuration dict
        repo_root: Optional repository root path
        names: Optional list of guideline names to compose (default: all)
        project_overrides: Whether to include project-specific overlays
        dry_min_shingles: Optional minimum shingles threshold for DRY detection

    Returns:
        Dict mapping guideline names to output file paths
    """
    from .engine import CompositionEngine

    engine = CompositionEngine(
        project_config or {},
        repo_root=repo_root,
    )
    return engine.compose_guidelines(
        packs_override=list(active_packs),
        names=list(names) if names is not None else None,
        project_overrides=project_overrides,
        dry_min_shingles=dry_min_shingles,
    )


__all__ = [
    "compose_guidelines",
]
