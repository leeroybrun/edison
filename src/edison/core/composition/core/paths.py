"""Composition-specific path resolution.

This module provides centralized path resolution logic that all registries,
composers, and discovery modules should use. It eliminates duplicate
path resolution logic across the codebase.

Architecture:
    - Core content: ALWAYS from bundled edison.data package
    - User overrides: ~/.edison/<type>/, ~/.edison/config/, ~/.edison/packs/
    - Project overrides: .edison/guidelines/, .edison/validators/, etc.
    - Project packs: .edison/packs/ (in addition to bundled + user packs)
    - NO .edison/core/ - that is legacy and not supported

Usage:
    resolver = CompositionPathResolver(repo_root)
    core_dir = resolver.core_dir  # Always bundled edison.data
    project_dir = resolver.project_dir  # .edison/
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_project_config_dir
from edison.core.packs.paths import PackRoot, get_pack_roots
from edison.data import get_data_path


@dataclass(frozen=True)
class ResolvedPaths:
    """Immutable container for resolved composition paths.
    
    Attributes:
        core_dir: Bundled core content directory (edison.data package)
        bundled_packs_dir: Bundled packs directory (edison.data/packs)
        user_dir: User configuration directory (~/<user-config-dir>)
        user_packs_dir: User-level packs directory (~/<user-config-dir>/packs)
        project_dir: Project configuration directory (.edison/)
        project_packs_dir: Project-level packs directory (.edison/packs/)
        repo_root: Repository root path
    """
    core_dir: Path
    bundled_packs_dir: Path
    user_dir: Path
    user_packs_dir: Path
    project_dir: Path
    project_packs_dir: Path
    repo_root: Path

    @property
    def uses_bundled_data(self) -> bool:
        """Always True - core content is always from bundled data."""
        return True


@dataclass(frozen=True)
class LayerContext:
    """Unified layer context for Edison extensibility.

    Encapsulates all resolved layer roots and derived config directories so
    subsystems can share a single source of truth and avoid drift.
    """

    repo_root: Path

    # Bundled Edison data (always present)
    core_dir: Path
    core_config_dir: Path

    # User layer (defaults to ~/.edison)
    user_dir: Path
    user_config_dir: Path

    # Project layer (.edison)
    project_dir: Path
    project_config_dir: Path
    project_local_config_dir: Path

    # Pack roots (bundled → user → project)
    pack_roots: tuple[PackRoot, PackRoot, PackRoot]

    @property
    def bundled_packs_dir(self) -> Path:
        return self.pack_roots[0].path

    @property
    def user_packs_dir(self) -> Path:
        return self.pack_roots[1].path

    @property
    def project_packs_dir(self) -> Path:
        return self.pack_roots[2].path

    def pack_root_paths(self) -> list[tuple[str, Path]]:
        """Return pack roots in low→high precedence order."""
        return [(r.kind, r.path) for r in self.pack_roots]


class CompositionPathResolver:
    """Centralized path resolution for all composition/layering operations.
    
    Architecture:
        - Core content (agents, validators, guidelines, rules, etc.) is ALWAYS
          loaded from the bundled edison.data package.
        - User-level overrides/additions are at ~/<user-config-dir>/<type>/ directories
          and user packs are at ~/<user-config-dir>/packs.
        - Project-level overrides/additions are at .edison/<type>/ directories:
          .edison/guidelines/, .edison/validators/, .edison/agents/, .edison/rules/
        - Project packs are at .edison/packs/
        - NO .edison/core/ - that is LEGACY and NOT SUPPORTED
    
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
            content_type: Optional content type hint (e.g., "agents", "validators").
                         Used for documentation purposes; does not affect path resolution.
        """
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.content_type = content_type
        self._resolved: Optional[ResolvedPaths] = None
        self._layer_context: Optional[LayerContext] = None
    
    def _resolve(self) -> ResolvedPaths:
        """Resolve paths - core is always bundled, project overrides at .edison/."""
        if self._resolved is not None:
            return self._resolved
        
        project_dir = get_project_config_dir(self.repo_root, create=False)
        from edison.core.utils.paths import get_user_config_dir
        user_dir = get_user_config_dir(create=False)
        
        # Core content is ALWAYS from bundled edison.data package
        core_dir = Path(get_data_path(""))
        bundled_packs_dir = Path(get_data_path("packs"))
        
        # Project-level packs directory
        project_packs_dir = project_dir / "packs"
        user_packs_dir = user_dir / "packs"
        
        self._resolved = ResolvedPaths(
            core_dir=core_dir,
            bundled_packs_dir=bundled_packs_dir,
            user_dir=user_dir,
            user_packs_dir=user_packs_dir,
            project_dir=project_dir,
            project_packs_dir=project_packs_dir,
            repo_root=self.repo_root,
        )
        return self._resolved
    
    @property
    def core_dir(self) -> Path:
        """Core content directory - ALWAYS bundled edison.data."""
        return self._resolve().core_dir

    @property
    def bundled_packs_dir(self) -> Path:
        """Bundled packs directory (edison.data/packs)."""
        return self._resolve().bundled_packs_dir

    @property
    def user_dir(self) -> Path:
        """User configuration directory (~/<user-config-dir>)."""
        return self._resolve().user_dir

    @property
    def user_packs_dir(self) -> Path:
        """User packs directory (~/<user-config-dir>/packs)."""
        return self._resolve().user_packs_dir
    
    @property
    def project_packs_dir(self) -> Path:
        """Project-level packs directory (.edison/packs/)."""
        return self._resolve().project_packs_dir
    
    @property
    def project_dir(self) -> Path:
        """Project configuration directory (.edison/)."""
        return self._resolve().project_dir
    
    @property
    def uses_bundled_data(self) -> bool:
        """Always True - core content is always from bundled data."""
        return True
    
    def get_project_content_dir(self, content_type: str) -> Path:
        """Get project-level content directory for a specific type.
        
        Args:
            content_type: Type of content (e.g., "guidelines", "validators", "agents", "rules")
        
        Returns:
            Path to .edison/<content_type>/
        """
        return self._resolve().project_dir / content_type
    
    def get_paths(self) -> ResolvedPaths:
        """Get all resolved paths as a dataclass."""
        return self._resolve()

    @property
    def layer_context(self) -> LayerContext:
        """Unified layer context for composition + config + loaders."""
        if self._layer_context is not None:
            return self._layer_context

        resolved = self._resolve()
        project_config_dir = resolved.project_dir / "config"
        project_local_config_dir = resolved.project_dir / "config.local"
        user_config_dir = resolved.user_dir / "config"
        core_config_dir = Path(get_data_path("config"))
        pack_roots = get_pack_roots(resolved.repo_root)

        self._layer_context = LayerContext(
            repo_root=resolved.repo_root,
            core_dir=resolved.core_dir,
            core_config_dir=core_config_dir,
            user_dir=resolved.user_dir,
            user_config_dir=user_config_dir,
            project_dir=resolved.project_dir,
            project_config_dir=project_config_dir,
            project_local_config_dir=project_local_config_dir,
            pack_roots=pack_roots,
        )
        return self._layer_context


@lru_cache(maxsize=32)
def get_resolved_paths(
    repo_root: Optional[Path] = None,
    content_type: Optional[str] = None,
) -> ResolvedPaths:
    """Cached path resolution for a given repo root and content type.
    
    This is a convenience function that caches results for performance.
    
    Args:
        repo_root: Repository root. Resolved automatically if not provided.
        content_type: Optional content type hint (does not affect resolution).
    
    Returns:
        ResolvedPaths with core_dir, project_dir, etc.
    """
    resolver = CompositionPathResolver(repo_root, content_type)
    return resolver.get_paths()


__all__ = [
    "CompositionPathResolver",
    "ResolvedPaths",
    "LayerContext",
    "get_resolved_paths",
]
