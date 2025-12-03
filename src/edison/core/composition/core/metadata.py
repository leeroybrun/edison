"""Unified metadata extraction for composition.

Provides consistent frontmatter parsing across all composition types:
- Agents
- Validators
- Guidelines
- Documents
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class CompositionMetadata:
    """Parsed frontmatter metadata from a composed file.

    Attributes:
        name: Entity name.
        description: Description text.
        version: Version string.
        model: AI model to use.
        tags: List of tags.
        requires_validation: Whether validation is required.
        constitution: Path to constitution file.
        extra: Additional metadata not in standard fields.
    """

    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    model: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    requires_validation: bool = False
    constitution: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompositionMetadata":
        """Create metadata from dictionary.

        Args:
            data: Frontmatter dictionary.

        Returns:
            CompositionMetadata instance.
        """
        known_fields = {
            "name",
            "description",
            "version",
            "model",
            "tags",
            "requires_validation",
            "constitution",
        }

        # Extract known fields
        kwargs = {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "version": data.get("version", "1.0.0"),
            "model": data.get("model"),
            "tags": data.get("tags", []),
            "requires_validation": data.get("requires_validation", False),
            "constitution": data.get("constitution"),
        }

        # Put unknown fields in extra
        extra = {k: v for k, v in data.items() if k not in known_fields}
        kwargs["extra"] = extra

        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary.

        Returns:
            Dictionary representation of metadata.
        """
        result: Dict[str, Any] = {}

        if self.name:
            result["name"] = self.name
        if self.description:
            result["description"] = self.description
        if self.version:
            result["version"] = self.version
        if self.model:
            result["model"] = self.model
        if self.tags:
            result["tags"] = self.tags
        if self.requires_validation:
            result["requires_validation"] = self.requires_validation
        if self.constitution:
            result["constitution"] = self.constitution

        # Merge extra fields
        result.update(self.extra)

        return result


class MetadataExtractor:
    """Extract YAML frontmatter from markdown files.

    Handles the standard frontmatter format:
    ---
    name: entity-name
    description: Entity description
    ...
    ---

    Content follows here...
    """

    # Pattern to match YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n",
        re.DOTALL,
    )

    def extract(self, content: str) -> tuple[CompositionMetadata, str]:
        """Extract frontmatter and content from markdown.

        Args:
            content: Full markdown content with optional frontmatter.

        Returns:
            Tuple of (metadata, remaining_content).
        """
        match = self.FRONTMATTER_PATTERN.match(content)

        if not match:
            return CompositionMetadata(), content

        frontmatter_str = match.group(1)
        remaining_content = content[match.end() :]

        try:
            frontmatter_dict = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError:
            return CompositionMetadata(), content

        if not isinstance(frontmatter_dict, dict):
            return CompositionMetadata(), content

        metadata = CompositionMetadata.from_dict(frontmatter_dict)
        return metadata, remaining_content

    def extract_from_file(self, path: Path) -> tuple[CompositionMetadata, str]:
        """Extract frontmatter from a file.

        Args:
            path: Path to markdown file.

        Returns:
            Tuple of (metadata, remaining_content).
        """
        content = path.read_text(encoding="utf-8")
        return self.extract(content)

    def has_frontmatter(self, content: str) -> bool:
        """Check if content has frontmatter.

        Args:
            content: Markdown content.

        Returns:
            True if frontmatter is present.
        """
        return bool(self.FRONTMATTER_PATTERN.match(content))

    def strip_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content.

        Args:
            content: Markdown content with optional frontmatter.

        Returns:
            Content without frontmatter.
        """
        _, remaining = self.extract(content)
        return remaining

    def update_frontmatter(
        self,
        content: str,
        updates: Dict[str, Any],
    ) -> str:
        """Update frontmatter fields in content.

        Args:
            content: Markdown content.
            updates: Fields to update or add.

        Returns:
            Content with updated frontmatter.
        """
        metadata, body = self.extract(content)

        # Merge updates into existing metadata
        data = metadata.to_dict()
        data.update(updates)

        # Regenerate frontmatter
        frontmatter_str = yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return f"---\n{frontmatter_str}---\n\n{body.lstrip()}"
