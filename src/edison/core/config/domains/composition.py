"""Domain-specific configuration for composition.

Provides cached access to composition-related configuration without
requiring direct ConfigManager usage or YAML parsing throughout the codebase.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from ..base import BaseDomainConfig
from edison.data import get_data_path

if TYPE_CHECKING:
    from ..manager import ConfigManager


class CompositionConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for composition settings.

    Provides typed, cached access to composition configuration including:
    - Deduplication settings (shingle size, min shingles, threshold)
    - Output paths configuration
    - Content type modes

    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Usage:
        comp = CompositionConfig(repo_root=Path("/path/to/project"))
        k = comp.shingle_size  # 12
        outputs = comp.outputs  # {...}
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        super().__init__(repo_root=repo_root)
        self._cached_composition_yaml: Optional[dict] = None

    def _config_section(self) -> str:
        return "composition"

    def _get_composition_yaml(self) -> dict:
        """Load composition.yaml with caching."""
        if self._cached_composition_yaml is None:
            composition_yaml_path = get_data_path("config") / "composition.yaml"
            if composition_yaml_path.exists():
                # Lazy import to avoid circular dependency
                from ..manager import ConfigManager
                mgr = ConfigManager(self._repo_root)
                self._cached_composition_yaml = mgr.load_yaml(composition_yaml_path)
            else:
                self._cached_composition_yaml = {}
        return self._cached_composition_yaml

    @cached_property
    def dry_detection(self) -> Dict[str, Any]:
        """Get DRY detection configuration.

        Returns:
            Dict with shingleSize, minShingles, threshold.
        """
        return self.section.get("dryDetection", {}) or {}

    @cached_property
    def shingle_size(self) -> int:
        """Get shingle size for deduplication.

        Returns:
            Number of words per shingle (default: 12).
        """
        return self.dry_detection.get("shingleSize", 12)

    @cached_property
    def min_shingles(self) -> int:
        """Get minimum shingles for duplicate detection.

        Returns:
            Minimum matching shingles threshold (default: 5).
        """
        return self.dry_detection.get("minShingles", 5)

    @cached_property
    def threshold(self) -> float:
        """Get similarity threshold for duplicate detection.

        Returns:
            Similarity threshold (0.0 - 1.0, default: 0.37).
        """
        return float(self.dry_detection.get("threshold", 0.37))

    @cached_property
    def outputs(self) -> Dict[str, Any]:
        """Get output path configuration.

        Returns:
            Dict with output configuration for all content types.
        """
        yaml_config = self._get_composition_yaml()
        return yaml_config.get("outputs", {}) or {}

    @cached_property
    def content_types(self) -> Dict[str, Any]:
        """Get content type definitions.

        Returns:
            Dict mapping content type name to its configuration.
        """
        yaml_config = self._get_composition_yaml()
        return yaml_config.get("content_types", {}) or {}

    def get_mode_for_type(self, content_type: str) -> str:
        """Get composition mode for a content type.

        Args:
            content_type: Type name (e.g., "agents", "guidelines")

        Returns:
            Mode string ("section", "concatenate", "yaml_merge").
        """
        type_config = self.content_types.get(content_type, {}) or {}
        return type_config.get("composition_mode", "section")


__all__ = ["CompositionConfig"]




