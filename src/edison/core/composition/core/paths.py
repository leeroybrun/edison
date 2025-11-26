"""Composition-specific path resolution.

This module provides centralized path resolution logic that all registries,
composers, and discovery modules should use. It eliminates duplicate
path resolution logic across the codebase.

Usage:
    resolver = CompositionPathResolver(repo_root)
    core_dir = resolver.core_dir
    packs_dir = resolver.packs_dir
    project_dir = resolver.project_dir
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_project_config_dir


@dataclass(frozen=True)
class ResolvedPaths:
    """Immutable container for resolved composition paths."""
    core_dir: Path
    packs_dir: Path
    project_dir: Path
    repo_root: Path
    uses_bundled_data: bool


class CompositionPathResolver:
    """Centralized path resolution for all composition/layering operations.
    
    Determines whether to use project-level directories or bundled data
    based on the presence of content in the project's .edison directory.
    
    This is the SINGLE SOURCE OF TRUTH for path resolution within composition.
    All composition registries should use this class.
    """
    
    def __init__(
        self,
        repo_root: Optional[Path] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """Initialize path resolver.
        
        Args:
            repo_root: Repository root. Resolved automatically if not provided.
            content_type: Optional content type to check for (e.g., "agents", "validators").
                         If provided, checks for that specific type.
                         If not provided, checks for any content.
        """
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.content_type = content_type
        self._resolved: Optional[ResolvedPaths] = None
    
    def _resolve(self) -> ResolvedPaths:
        """Resolve paths based on project content presence."""
        if self._resolved is not None:
            return self._resolved
        
        project_dir = get_project_config_dir(self.repo_root, create=False)
        project_core = project_dir / "core"
        project_packs = project_dir / "packs"
        
        # Check if project has relevant content
        has_project_content = self._has_project_content(
            project_core, project_packs
        )
        
        if has_project_content:
            core_dir = project_core
            packs_dir = project_packs
            uses_bundled = False
        else:
            # Fall back to bundled data
            from edison.data import get_data_path
            core_dir = Path(get_data_path(""))
            packs_dir = Path(get_data_path("packs"))
            uses_bundled = True
        
        self._resolved = ResolvedPaths(
            core_dir=core_dir,
            packs_dir=packs_dir,
            project_dir=project_dir,
            repo_root=self.repo_root,
            uses_bundled_data=uses_bundled,
        )
        return self._resolved
    
    def _has_project_content(self, project_core: Path, project_packs: Path) -> bool:
        """Check if project has content for the specified type (or any type)."""
        if self.content_type:
            # Check for specific content type
            type_dir = project_core / self.content_type
            has_core = type_dir.exists() and any(type_dir.rglob("*.md"))
            has_packs = project_packs.exists() and any(
                p for p in project_packs.rglob("*.md")
                if f"/{self.content_type}/" in str(p)
            )
            return has_core or has_packs
        else:
            # Check for any content
            has_core = project_core.exists() and any(project_core.rglob("*.md"))
            has_packs = project_packs.exists() and any(project_packs.rglob("*.md"))
            return has_core or has_packs
    
    @property
    def core_dir(self) -> Path:
        """Core content directory (bundled or project-level)."""
        return self._resolve().core_dir
    
    @property
    def packs_dir(self) -> Path:
        """Packs directory (bundled or project-level)."""
        return self._resolve().packs_dir
    
    @property
    def project_dir(self) -> Path:
        """Project configuration directory (.edison)."""
        return self._resolve().project_dir
    
    @property
    def uses_bundled_data(self) -> bool:
        """Whether bundled data is being used (vs project-level)."""
        return self._resolve().uses_bundled_data
    
    def get_paths(self) -> ResolvedPaths:
        """Get all resolved paths as a dataclass."""
        return self._resolve()


# Backward compatibility alias
UnifiedPathResolver = CompositionPathResolver


@lru_cache(maxsize=32)
def get_resolved_paths(
    repo_root: Optional[Path] = None,
    content_type: Optional[str] = None,
) -> ResolvedPaths:
    """Cached path resolution for a given repo root and content type.
    
    This is a convenience function that caches results for performance.
    
    Args:
        repo_root: Repository root. Resolved automatically if not provided.
        content_type: Optional content type to check for.
    
    Returns:
        ResolvedPaths with core_dir, packs_dir, project_dir, etc.
    """
    resolver = CompositionPathResolver(repo_root, content_type)
    return resolver.get_paths()


__all__ = [
    "CompositionPathResolver",
    "UnifiedPathResolver",  # Backward compatibility
    "ResolvedPaths",
    "get_resolved_paths",
]
