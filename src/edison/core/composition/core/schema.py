"""Composition schema loaded from composition.yaml.

Defines content types and known sections for the unified section system.

The unified 4-concept system uses:
- SECTION markers: <!-- SECTION: name -->...<!-- /SECTION: name -->
- EXTEND markers: <!-- EXTEND: name -->...<!-- /EXTEND -->
- Include sections: {{include-section:path#name}}
- Reference sections: {{reference-section:path#name|purpose}}

Convention: Use 'composed-additions' as the standard section for pack/project content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from edison.data import get_data_path


@dataclass
class SectionSchema:
    """Schema for a known section."""
    name: str
    mode: str  # "replace" or "append"
    description: str = ""


@dataclass
class ContentTypeSchema:
    """Schema for a single content type."""
    name: str
    description: str
    known_sections: List[SectionSchema] = field(default_factory=list)
    composition_mode: str = "sections"  # "sections" or "concatenate" or "yaml_merge"
    dedupe: bool = False
    merge_key: Optional[str] = None  # For yaml_merge mode
    
    def get_known_section_names(self) -> Set[str]:
        """Return set of known section names."""
        return {s.name for s in self.known_sections}
    
    def is_section_extensible(self, section_name: str) -> bool:
        """Check if a section can be extended (mode == 'append')."""
        for s in self.known_sections:
            if s.name == section_name:
                return s.mode == "append"
        return False


class CompositionSchema:
    """Load and access composition schema from YAML.
    
    Schema defines:
    - Content types (agents, validators, guidelines, etc.)
    - Known sections per content type with modes (replace/append)
    - Composition mode (sections, concatenate, yaml_merge)
    - Validation rules
    
    The unified section system eliminates deprecated placeholders:
    - No more {{SECTION:Name}} placeholders
    - No more {{EXTENSIBLE_SECTIONS}} or {{APPEND_SECTIONS}}
    - Use <!-- SECTION: name --> and <!-- EXTEND: name --> instead
    """
    
    _instance: Optional["CompositionSchema"] = None
    
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data
        self.version = data.get("version", "2.0")
        self.content_types: Dict[str, ContentTypeSchema] = {}
        
        for name, cfg in data.get("content_types", {}).items():
            # Parse known_sections into SectionSchema objects
            known_sections = []
            for section_data in cfg.get("known_sections", []):
                known_sections.append(SectionSchema(
                    name=section_data.get("name", ""),
                    mode=section_data.get("mode", "append"),
                    description=section_data.get("description", ""),
                ))
            
            self.content_types[name] = ContentTypeSchema(
                name=name,
                description=cfg.get("description", ""),
                known_sections=known_sections,
                composition_mode=cfg.get("composition_mode", "sections"),
                dedupe=cfg.get("dedupe", False),
                merge_key=cfg.get("merge_key"),
            )
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CompositionSchema":
        """Load schema from composition.yaml."""
        if cls._instance is not None and path is None:
            return cls._instance
        
        if path is None:
            path = Path(get_data_path("config")) / "composition.yaml"
        
        from edison.core.utils.io import read_yaml
        data = read_yaml(path, default={})
        instance = cls(data)
        
        if path is None:
            cls._instance = instance
        
        return instance
    
    @classmethod
    def reset_cache(cls) -> None:
        """Reset cached instance (for testing)."""
        cls._instance = None
    
    def get_content_type(self, name: str) -> ContentTypeSchema:
        """Get schema for a content type."""
        if name not in self.content_types:
            raise ValueError(f"Unknown content type: {name}")
        return self.content_types[name]
    
    def get_known_sections(self, content_type: str) -> Set[str]:
        """Return known section names for a content type."""
        schema = self.get_content_type(content_type)
        return schema.get_known_section_names()
    
    def is_section_extensible(self, content_type: str, section_name: str) -> bool:
        """Check if a section in a content type can be extended."""
        schema = self.get_content_type(content_type)
        return schema.is_section_extensible(section_name)
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """Access raw schema data."""
        return self._data
