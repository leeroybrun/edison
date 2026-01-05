"""Vendor mount executor.

Creates symlinks or copies from vendor directories to project paths.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from edison.core.vendors.models import MountResult, VendorMount


class MountExecutor:
    """Executes vendor mount operations (symlinks and copies)."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize mount executor.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = repo_root

    def execute(
        self,
        mount: VendorMount,
        vendor_path: Path,
        force: bool = False,
        dry_run: bool = False,
    ) -> MountResult:
        """Execute a mount operation.

        Args:
            mount: Mount configuration
            vendor_path: Path to vendor checkout
            force: If True, remove existing target before mounting
            dry_run: If True, report what would happen without doing it

        Returns:
            MountResult with operation status
        """
        repo_root_resolved = self.repo_root.resolve()
        vendor_root_resolved = vendor_path.resolve()

        source_rel = Path(mount.source_path)
        target_rel = Path(mount.target_path)

        if source_rel.is_absolute() or str(source_rel).startswith("~"):
            return MountResult(
                success=False,
                error=f"Unsafe mount source path: {mount.source_path}",
            )
        if target_rel.is_absolute() or str(target_rel).startswith("~"):
            return MountResult(
                success=False,
                error=f"Unsafe mount target path: {mount.target_path}",
            )

        source = (vendor_path / source_rel).resolve()
        if not source.is_relative_to(vendor_root_resolved):
            return MountResult(
                success=False,
                error=f"Refusing to mount source outside vendor root: {source}",
            )

        target = (self.repo_root / target_rel).resolve()
        if not target.is_relative_to(repo_root_resolved):
            return MountResult(
                success=False,
                error=f"Refusing to mount target outside repo root: {target}",
            )

        if dry_run:
            return MountResult(
                success=True,
                path=str(target),
                would_create=not target.exists(),
            )

        try:
            # Copy mounts must not dereference symlinks that escape the vendor root.
            # This prevents exfiltration of arbitrary files into the project via crafted vendor content.
            if mount.mount_type == "copy" and source.exists():
                if source.is_dir():
                    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
                        dirpath_path = Path(dirpath)
                        for name in list(dirnames) + list(filenames):
                            p = dirpath_path / name
                            if p.is_symlink() and not p.resolve().is_relative_to(vendor_root_resolved):
                                return MountResult(
                                    success=False,
                                    path=str(target),
                                    error=f"Refusing to copy symlink outside vendor root: {p}",
                                )
                elif source.is_symlink() and not source.resolve().is_relative_to(vendor_root_resolved):
                    return MountResult(
                        success=False,
                        path=str(target),
                        error=f"Refusing to copy symlink outside vendor root: {source}",
                    )

            # Handle existing target
            if target.exists() or target.is_symlink():
                if not force:
                    return MountResult(
                        success=False,
                        path=str(target),
                        error=f"Target already exists: {target}",
                    )
                # Remove existing
                if target.is_symlink():
                    target.unlink()
                elif target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)

            # Execute mount
            if mount.mount_type == "symlink":
                target.symlink_to(source, target_is_directory=source.is_dir())
            elif mount.mount_type == "copy":
                if source.is_dir():
                    shutil.copytree(source, target, symlinks=True, ignore_dangling_symlinks=True)
                else:
                    shutil.copy2(source, target, follow_symlinks=False)
            else:
                return MountResult(
                    success=False,
                    error=f"Unknown mount type: {mount.mount_type}",
                )

            return MountResult(
                success=True,
                path=str(target),
            )

        except Exception as e:
            return MountResult(
                success=False,
                path=str(target),
                error=str(e),
            )


__all__ = ["MountExecutor"]
