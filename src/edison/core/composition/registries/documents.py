#!/usr/bin/env python3
"""
Edison Document Template Composition

Composes task and QA document templates from core, packs, and project layers.
Document templates use YAML frontmatter for metadata and Handlebars-style
variables for dynamic content.

Output templates are generated to:
- .edison/_generated/documents/TASK.md
- .edison/_generated/documents/QA.md
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from edison.core.entity import BaseRegistry
from edison.core.utils.paths import PathResolver

# Import from core composition system
from ..core import (
    LayeredComposer,
    LayerSource,
)
from ..output.writer import CompositionFileWriter


class DocumentTemplateError(RuntimeError):
    """Base error for document template composition."""


class DocumentTemplateNotFoundError(DocumentTemplateError):
    """Raised when a requested document template does not exist."""


@dataclass
class DocumentTemplate:
    """Document template reference."""
    name: str
    path: Path
    
    @classmethod
    def from_layer_source(cls, source: LayerSource) -> "DocumentTemplate":
        """Create DocumentTemplate from unified LayerSource."""
        return cls(name=source.entity_name, path=source.path)


class DocumentTemplateRegistry(BaseRegistry[DocumentTemplate]):
    """Discover and compose document templates using the core composition system.
    
    Templates are discovered from:
    - Core: src/edison/data/templates/documents/
    - Packs: .edison/packs/{pack}/templates/documents/
    - Project: .edison/project/templates/documents/
    
    Output is generated to: .edison/_generated/documents/
    """
    
    entity_type: str = "document"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        super().__init__(project_root)
        
        # Use unified composer for discovery
        self._composer = LayeredComposer(
            repo_root=self.project_root, 
            content_type="documents",
        )
    
    # ------- BaseRegistry Interface Implementation -------
    
    def discover_core(self) -> Dict[str, DocumentTemplate]:
        """Discover core document templates."""
        sources = self._composer.discover_core()
        return {name: DocumentTemplate.from_layer_source(src) for name, src in sources.items()}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, DocumentTemplate]:
        """Discover document templates from packs (both new and overlays)."""
        result: Dict[str, DocumentTemplate] = {}
        existing = set(self._composer.discover_core().keys())
        
        for pack in packs:
            pack_new = self._composer.discover_pack_new(pack, existing)
            for name, source in pack_new.items():
                result[name] = DocumentTemplate.from_layer_source(source)
            existing.update(pack_new.keys())
        
        return result
    
    def discover_project(self) -> Dict[str, DocumentTemplate]:
        """Discover project-level document templates."""
        existing = set(self._composer.discover_core().keys())
        project_new = self._composer.discover_project_new(existing)
        return {name: DocumentTemplate.from_layer_source(src) for name, src in project_new.items()}
    
    def exists(self, name: str) -> bool:
        """Check if a document template exists."""
        return name in self._composer.discover_core()
    
    def get(self, name: str) -> Optional[DocumentTemplate]:
        """Get a document template by name."""
        templates = self.discover_core()
        return templates.get(name)
    
    def get_all(self) -> List[DocumentTemplate]:
        """Return all core document templates."""
        return list(self.discover_core().values())
    
    # ------- Composition -------
    
    def compose_document(self, template_name: str, packs: List[str]) -> str:
        """Compose a single document template from core + pack + project overlays.
        
        Args:
            template_name: Template name (e.g., "TASK", "QA")
            packs: List of packs to include
            
        Returns:
            Composed template content
        """
        try:
            composed = self._composer.compose(template_name, packs)
        except Exception as e:
            if "not found" in str(e).lower():
                raise DocumentTemplateNotFoundError(str(e)) from e
            raise DocumentTemplateError(str(e)) from e
        
        return composed
    
    def compose_all(self, packs: List[str]) -> Dict[str, str]:
        """Compose all document templates.
        
        Args:
            packs: List of packs to include
            
        Returns:
            Dict mapping template names to composed content
        """
        results: Dict[str, str] = {}
        
        # Get all available templates
        all_templates = set(self.discover_core().keys())
        all_templates.update(self.discover_packs(packs).keys())
        all_templates.update(self.discover_project().keys())
        
        for name in all_templates:
            try:
                results[name] = self.compose_document(name, packs)
            except DocumentTemplateNotFoundError:
                continue  # Skip missing templates
        
        return results
    
    def write_composed(self, packs: List[str]) -> List[Path]:
        """Compose and write all document templates to _generated/documents/.

        Args:
            packs: List of packs to include

        Returns:
            List of paths to written files
        """
        composed = self.compose_all(packs)
        output_dir = self.project_dir / "_generated" / "documents"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Use CompositionFileWriter for consistent file output
        writer = CompositionFileWriter()
        written: List[Path] = []
        for name, content in composed.items():
            output_path = output_dir / f"{name}.md"
            written_path = writer.write_text(output_path, content)
            written.append(written_path)

        return written


def compose_document(
    template_name: str, 
    packs: List[str], 
    *, 
    project_root: Optional[Path] = None,
) -> str:
    """Functional wrapper for DocumentTemplateRegistry.compose_document."""
    registry = DocumentTemplateRegistry(project_root=project_root)
    return registry.compose_document(template_name, packs)


__all__ = [
    "DocumentTemplateRegistry",
    "DocumentTemplateError",
    "DocumentTemplateNotFoundError",
    "DocumentTemplate",
    "compose_document",
]

