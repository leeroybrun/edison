"""Unified composition configuration domain.

CompositionConfig is the ONLY way to access composition.yaml settings.
All other classes (ComposableTypesManager, AdapterLoader) use this.

This module provides:
- SectionSchema: Schema for a known section
- ContentTypeConfig: Configuration for a composable content type
- AdapterSyncConfig: Sync configuration for an adapter
- AdapterConfig: Configuration for a platform adapter
- CompositionConfig: The main configuration accessor
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..base import BaseDomainConfig
from edison.data import get_data_path
from edison.core.utils.profiling import span


@dataclass
class SectionSchema:
    """Schema for a known section in content types."""
    name: str
    mode: str  # "replace" or "append"
    description: str = ""


@dataclass
class ContentTypeConfig:
    """Configuration for a content type."""
    name: str
    enabled: bool
    description: str
    composition_mode: str
    dedupe: bool
    registry: Optional[str]
    content_path: str
    file_pattern: str
    output_path: str
    filename_pattern: str
    cli_flag: str
    # Paths are relative to the content-type root (e.g., guidelines/).
    # Used to exclude include-only or private content from being composed.
    exclude_globs: List[str] = field(default_factory=list)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    known_sections: List[SectionSchema] = field(default_factory=list)
    
    def get_known_section_names(self) -> Set[str]:
        """Return set of known section names."""
        return {s.name for s in self.known_sections}
    
    def is_section_extensible(self, section_name: str) -> bool:
        """Check if a section can be extended (mode == 'append')."""
        for s in self.known_sections:
            if s.name == section_name:
                return s.mode == "append"
        return False


@dataclass
class AdapterSyncConfig:
    """Sync configuration for an adapter."""
    name: str
    enabled: bool
    source: str
    destination: str
    filename_pattern: str


@dataclass
class AdapterConfig:
    """Configuration for a platform adapter."""
    name: str
    enabled: bool
    adapter_class: str
    description: str
    output_path: str
    filename: Optional[str]
    sync: Dict[str, AdapterSyncConfig] = field(default_factory=dict)


class CompositionConfig(BaseDomainConfig):
    """Unified configuration accessor for composition settings.
    
    This is the SINGLE SOURCE OF TRUTH for composition.yaml access.
    All composition-related code should use this class.
    
    Usage:
        comp = CompositionConfig(repo_root=Path("/path/to/project"))
        
        # Access defaults
        shingle_size = comp.shingle_size
        
        # Access content types
        for ct in comp.get_enabled_content_types():
            print(ct.name, ct.output_path)
        
        # Access adapters
        for adapter in comp.get_enabled_adapters():
            print(adapter.name, adapter.adapter_class)
    """
    
    def __init__(self, repo_root: Optional[Path] = None) -> None:
        super().__init__(repo_root=repo_root)
        self._cached_composition_yaml: Optional[Dict[str, Any]] = None
    
    def _config_section(self) -> str:
        return "composition"  # For BaseDomainConfig compatibility
    
    @cached_property
    def _composition_yaml(self) -> Dict[str, Any]:
        """Load composition.yaml with caching.
        
        Uses ConfigManager's pack-aware loading (core > packs > project).
        All composition config is under the `composition:` key.
        """
        if self._cached_composition_yaml is not None:
            return self._cached_composition_yaml

        with span("composition.config.load"):
            # BaseDomainConfig already loaded the full merged config via the centralized cache.
            # Reuse it to avoid repeated disk IO during composition.
            full_config = self._config
            self._cached_composition_yaml = full_config.get("composition", {})

        return self._cached_composition_yaml
    
    # =========================================================================
    # DEFAULTS
    # =========================================================================
    
    @cached_property
    def defaults(self) -> Dict[str, Any]:
        """Get defaults section."""
        return self._composition_yaml.get("defaults", {})
    
    @property
    def shingle_size(self) -> int:
        """Get shingle size for deduplication."""
        return self.defaults.get("dedupe", {}).get("shingle_size", 12)
    
    @property
    def min_shingles(self) -> int:
        """Get minimum shingles for duplicate detection."""
        return self.defaults.get("dedupe", {}).get("min_shingles", 5)
    
    @property
    def threshold(self) -> float:
        """Get similarity threshold for duplicate detection."""
        return float(self.defaults.get("dedupe", {}).get("threshold", 0.37))
    
    @property
    def generated_header(self) -> str:
        """Get generated file header template."""
        return self.defaults.get("generated_header", "")
    
    @property
    def default_composition_mode(self) -> str:
        """Get default composition mode."""
        return self.defaults.get("composition_mode", "section_merge")
    
    # =========================================================================
    # CONTENT TYPES
    # =========================================================================
    
    @cached_property
    def content_types(self) -> Dict[str, ContentTypeConfig]:
        """Get all content type configurations."""
        raw = self._composition_yaml.get("content_types", {})
        result: Dict[str, ContentTypeConfig] = {}
        for name, cfg in raw.items():
            # Parse known_sections if present
            known_sections: List[SectionSchema] = []
            for section_data in cfg.get("known_sections", []):
                # Support shorthand list form:
                #   known_sections: [intro, usage]
                if isinstance(section_data, str):
                    known_sections.append(SectionSchema(name=section_data, mode="append", description=""))
                    continue
                if isinstance(section_data, dict):
                    known_sections.append(
                        SectionSchema(
                            name=section_data.get("name", ""),
                            mode=section_data.get("mode", "append"),
                            description=section_data.get("description", ""),
                        )
                    )
            
            result[name] = ContentTypeConfig(
                name=name,
                enabled=cfg.get("enabled", True),
                description=cfg.get("description", ""),
                composition_mode=cfg.get("composition_mode", self.default_composition_mode),
                dedupe=cfg.get("dedupe", False),
                registry=cfg.get("registry"),
                content_path=cfg.get("content_path", name),
                file_pattern=cfg.get("file_pattern", "*.md"),
                exclude_globs=cfg.get("exclude_globs", []) or [],
                output_path=cfg.get("output_path", ""),
                filename_pattern=cfg.get("filename_pattern", "{name}.md"),
                cli_flag=cfg.get("cli_flag", name.replace("_", "-")),
                output_mapping=cfg.get("output_mapping", {}),
                known_sections=known_sections,
            )
        return result
    
    def get_content_type(self, name: str) -> Optional[ContentTypeConfig]:
        """Get a specific content type configuration."""
        return self.content_types.get(name)
    
    def get_enabled_content_types(self) -> List[ContentTypeConfig]:
        """Get all enabled content types."""
        return [ct for ct in self.content_types.values() if ct.enabled]
    
    def get_content_type_by_cli_flag(self, flag: str) -> Optional[ContentTypeConfig]:
        """Get content type by CLI flag name."""
        for ct in self.content_types.values():
            if ct.cli_flag == flag:
                return ct
        return None
    
    # =========================================================================
    # ADAPTERS
    # =========================================================================
    
    @cached_property
    def adapters(self) -> Dict[str, AdapterConfig]:
        """Get all adapter configurations."""
        raw = self._composition_yaml.get("adapters", {})
        result: Dict[str, AdapterConfig] = {}
        for name, cfg in raw.items():
            sync_configs: Dict[str, AdapterSyncConfig] = {}
            for sync_name, sync_cfg in (cfg.get("sync") or {}).items():
                sync_configs[sync_name] = AdapterSyncConfig(
                    name=sync_name,
                    enabled=sync_cfg.get("enabled", True),
                    source=sync_cfg.get("source", ""),
                    destination=sync_cfg.get("destination", ""),
                    filename_pattern=sync_cfg.get("filename_pattern", "{name}.md"),
                )
            result[name] = AdapterConfig(
                name=name,
                enabled=cfg.get("enabled", True),
                adapter_class=cfg.get("adapter_class", ""),
                description=cfg.get("description", ""),
                output_path=cfg.get("output_path", ""),
                filename=cfg.get("filename"),
                sync=sync_configs,
            )
        return result
    
    def get_adapter(self, name: str) -> Optional[AdapterConfig]:
        """Get a specific adapter configuration."""
        return self.adapters.get(name)
    
    def get_enabled_adapters(self) -> List[AdapterConfig]:
        """Get all enabled adapters."""
        return [a for a in self.adapters.values() if a.enabled]
    
    def is_adapter_enabled(self, name: str) -> bool:
        """Check if an adapter is enabled."""
        adapter = self.get_adapter(name)
        return adapter is not None and adapter.enabled
    
    # =========================================================================
    # PATH RESOLUTION
    # =========================================================================
    
    def resolve_output_path(self, path_template: str) -> Path:
        """Resolve output path with variable substitution.
        
        Supports {{PROJECT_EDISON_DIR}} placeholder.
        """
        if not path_template:
            return self.repo_root
        
        from edison.core.utils.paths import get_project_config_dir
        project_dir = get_project_config_dir(self._repo_root)
        
        path_str = path_template.replace(
            "{{PROJECT_EDISON_DIR}}", str(project_dir)
        )
        
        path = Path(path_str)
        if not path.is_absolute():
            path = self.repo_root / path
        
        return path
    
    def get_content_type_output_dir(self, type_name: str) -> Optional[Path]:
        """Get resolved output directory for a content type."""
        ct = self.get_content_type(type_name)
        if not ct or not ct.enabled:
            return None
        return self.resolve_output_path(ct.output_path)
    
    def get_adapter_output_dir(self, adapter_name: str) -> Optional[Path]:
        """Get resolved output directory for an adapter."""
        adapter = self.get_adapter(adapter_name)
        if not adapter or not adapter.enabled:
            return None
        return self.resolve_output_path(adapter.output_path)


__all__ = [
    "CompositionConfig",
    "ContentTypeConfig",
    "SectionSchema",
    "AdapterConfig",
    "AdapterSyncConfig",
]
