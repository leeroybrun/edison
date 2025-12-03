#!/usr/bin/env python3
"""Edison Document Template Registry.

Composes task and QA document templates from core, packs, and project layers.
Document templates use YAML frontmatter for metadata and Handlebars-style
variables for dynamic content.

Architecture:
    CompositionBase → ComposableRegistry → DocumentTemplateRegistry
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from edison.core.entity.composable_registry import ComposableRegistry


class DocumentTemplateError(RuntimeError):
    """Base error for document template composition."""


class DocumentTemplateNotFoundError(DocumentTemplateError):
    """Raised when a requested document template does not exist."""


@dataclass
class DocumentTemplate:
    """Document template reference."""
    name: str
    path: Path


class DocumentTemplateRegistry(ComposableRegistry[str]):
    """Registry for discovering and composing document templates.

    Extends ComposableRegistry with document-specific:
    - Template discovery from documents/ directories
    - Write to _generated/documents/

    Templates are discovered from:
    - Core: bundled edison.data/documents/
    - Packs: .edison/packs/{pack}/documents/
    - Project: .edison/documents/
    """

    content_type: ClassVar[str] = "documents"
    file_pattern: ClassVar[str] = "*.md"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": True,
        "enable_dedupe": False,
        "enable_template_processing": True,
    }

    # ------- Document-Specific Methods -------

    def get_template(self, name: str) -> Optional[DocumentTemplate]:
        """Get a document template by name."""
        all_docs = self.discover_all()
        if name in all_docs:
            return DocumentTemplate(name=name, path=all_docs[name])
        return None

    def get_all_templates(self) -> List[DocumentTemplate]:
        """Return all document templates."""
        all_docs = self.discover_all()
        return [DocumentTemplate(name=name, path=path) for name, path in all_docs.items()]

    def compose_document(
        self,
        template_name: str,
        packs: Optional[List[str]] = None,
    ) -> str:
        """Compose a single document template.

        Args:
            template_name: Template name (e.g., "TASK", "QA")
            packs: List of packs to include

        Returns:
            Composed template content
        """
        result = self.compose(template_name, packs)
        if result is None:
            raise DocumentTemplateNotFoundError(
                f"Document template '{template_name}' not found"
            )
        return result

    def write_composed(self, packs: Optional[List[str]] = None) -> List[Path]:
        """Compose and write all document templates to _generated/documents/.

        Args:
            packs: List of packs to include

        Returns:
            List of paths to written files
        """
        packs = packs or self.get_active_packs()
        all_names = self.list_names(packs)
        output_dir = self.project_dir / "_generated" / "documents"
        output_dir.mkdir(parents=True, exist_ok=True)

        written: List[Path] = []
        for name in all_names:
            try:
                content = self.compose_document(name, packs)
                output_path = output_dir / f"{name}.md"
                self.writer.write_text(output_path, content)
                written.append(output_path)
            except DocumentTemplateNotFoundError:
                continue

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
