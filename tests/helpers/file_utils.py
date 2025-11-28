"""File operation utilities for test helpers.

Consolidates file operations used across test environment setup.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def copy_if_different(src: Path, dst: Path) -> None:
    """Copy file only if source and destination are different.

    This prevents unnecessary file operations when setting up test environments
    where the source and destination might be the same path.

    Args:
        src: Source file path
        dst: Destination file path
    """
    if not src.exists():
        return

    # Resolve to avoid issues with symlinks and relative paths
    src_resolved = src.resolve()
    dst_resolved = dst.resolve()

    if src_resolved != dst_resolved:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)


def copy_tree_if_different(src: Path, dst: Path) -> None:
    """Copy directory tree only if source and destination are different.

    Args:
        src: Source directory path
        dst: Destination directory path
    """
    if not src.exists():
        return

    # Resolve to avoid issues with symlinks and relative paths
    src_resolved = src.resolve()
    dst_resolved = dst.resolve()

    if src_resolved != dst_resolved:
        shutil.copytree(src, dst, dirs_exist_ok=True)
