"""Composition schema loaded from composition.yaml.

Defines content types, known sections, and placeholders.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class ContentTypeSchema:
    """Schema for a single content type."""
    name: str
    description: str
    known_sections: List[Dict[str, Any]]
    extensible_placeholder: str
    append_placeholder: str
    composition_mode: str = "sections"  # "sections" or "concatenate" or "yaml_merge"
    dedupe: bool = False
    
    def get_known_section_names(self) -> Set[str]:
        """Return set of known section names."""
        return {s["name"] for s in self.known_sections}
    
    def get_placeholder(self, section_name: str) -> Optional[str]:
        """Return placeholder string for a section."""
        for s in self.known_sections:
            if s["name"] == section_name:
                return s.get("placeholder")
        return None


class CompositionSchema:
    """Load and access composition schema from YAML.
    
    Schema defines:
    - Content types (agents, validators, guidelines, etc.)
    - Known sections per content type
    - Placeholder patterns
    - Validation rules
    """
    
    _instance: Optional["CompositionSchema"] = None
    
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data
        self.version = data.get("version", "1.0")
        self.content_types: Dict[str, ContentTypeSchema] = {}
        
        for name, cfg in data.get("content_types", {}).items():
            self.content_types[name] = ContentTypeSchema(
                name=name,
                description=cfg.get("description", ""),
                known_sections=cfg.get("known_sections", []),
                extensible_placeholder=cfg.get("extensible_placeholder", "{{EXTENSIBLE_SECTIONS}}"),
                append_placeholder=cfg.get("append_placeholder", "{{APPEND_SECTIONS}}"),
                composition_mode=cfg.get("composition_mode", "sections"),
                dedupe=cfg.get("dedupe", False),
            )
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CompositionSchema":
        """Load schema from composition.yaml."""
        if cls._instance is not None and path is None:
            return cls._instance
        
        if path is None:
            from edison.data import get_data_path
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
    
    def get_placeholder(self, content_type: str, section_name: str) -> Optional[str]:
        """Get placeholder for a section."""
        schema = self.get_content_type(content_type)
        return schema.get_placeholder(section_name)
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """Access raw schema data."""
        return self._data



