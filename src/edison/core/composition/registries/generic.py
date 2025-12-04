"""Generic config-driven registry for simple content types.

GenericRegistry allows creating registries dynamically via constructor parameters
instead of class attributes. It loads strategy config from composition.yaml
under `composition.content_types.{content_type}`.

This is used for content types that don't need custom post-processing logic:
- roots (canonical entry points like AGENTS.md)
- clients (client-specific markdown)
- documents (when no custom logic needed)
- cursor rules (.mdc files)

Usage:
    # Standard markdown content
    roots = GenericRegistry("roots", project_root=project_root)
    roots.write_all(output_dir, packs)

    # Cursor rules with custom extension and nested path
    cursor = GenericRegistry(
        content_type="clients/cursor/rules",
        file_pattern="*.mdc",
        project_root=project_root,
    )
    cursor.write_all(Path(".cursor/rules"), packs)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ._base import ComposableRegistry


class GenericRegistry(ComposableRegistry[str]):
    """Config-driven registry for simple content types.

    Unlike specialized registries (AgentRegistry, ValidatorRegistry) that define
    content_type as a class attribute, GenericRegistry accepts it as a constructor
    parameter. Strategy config is loaded from composition.yaml.

    Supports:
    - Custom content_type paths (e.g., "clients/cursor/rules" for nested dirs)
    - Custom file patterns (e.g., "*.mdc" for cursor rules)
    - Automatic extension detection from file_pattern

    Attributes:
        content_type: The content type name/path (e.g., "roots", "clients/cursor/rules")
        file_pattern: Glob pattern for matching files (default: "*.md")

    Example:
        # Standard registry
        roots = GenericRegistry("roots", project_root=project_root)
        roots.write_all(output_dir / "roots", packs=["python"])

        # Nested path with custom extension
        cursor = GenericRegistry(
            content_type="clients/cursor/rules",
            file_pattern="*.mdc",
            project_root=project_root,
        )
        cursor.write_all(Path(".cursor/rules"), packs=["python"])
    """

    # Override class attributes with instance-level values
    content_type: str = ""  # Will be set in __init__
    file_pattern: str = "*.md"  # Will be set in __init__

    def __init__(
        self,
        content_type: str,
        project_root: Optional[Path] = None,
        file_pattern: str = "*.md",
    ) -> None:
        """Initialize a generic registry for the given content type.

        Args:
            content_type: Content type name or path (e.g., "roots", "clients/cursor/rules").
                Can be a nested path - will be used for directory discovery:
                - Core: data/{content_type}/
                - Pack: data/packs/{pack}/{content_type}/
                - Project: .edison/{content_type}/
                Config lookup uses the full path: composition.content_types.{content_type}
            project_root: Project root directory. Auto-detected if not provided.
            file_pattern: Glob pattern for files (default: "*.md").
                Extension is extracted for output files (e.g., "*.mdc" -> ".mdc").
        """
        # Set instance attributes BEFORE calling super().__init__
        # This is required because ComposableRegistry validates content_type
        self._content_type = content_type
        self._file_pattern = file_pattern
        super().__init__(project_root)

    @property
    def content_type(self) -> str:  # type: ignore[override]
        """Return the content type set via constructor."""
        return self._content_type

    @property
    def file_pattern(self) -> str:  # type: ignore[override]
        """Return the file pattern set via constructor."""
        return self._file_pattern

    @property
    def file_extension(self) -> str:
        """Extract file extension from file_pattern.

        Examples:
            "*.md" -> ".md"
            "*.mdc" -> ".mdc"
            "*.yaml" -> ".yaml"
        """
        # Extract extension from pattern like "*.md" or "*.mdc"
        if self._file_pattern.startswith("*."):
            return self._file_pattern[1:]  # "*.md" -> ".md"
        elif self._file_pattern.startswith("*"):
            return self._file_pattern[1:]  # "*md" -> "md" (edge case)
        else:
            # Fallback - try to extract from pattern
            return ".md"

    # get_strategy_config() is inherited from ComposableRegistry
    # It reads from composition.yaml using self.content_type property

    def write_all(
        self,
        output_dir: Path,
        packs: Optional[List[str]] = None,
    ) -> List[Path]:
        """Compose and write all content of this type to output directory.

        Discovers all entities, composes each one, and writes to output_dir.
        Creates output_dir if it doesn't exist.

        File extension is derived from file_pattern (e.g., "*.mdc" -> ".mdc").

        Args:
            output_dir: Directory to write composed files to.
            packs: Optional list of active pack names. Uses get_active_packs() if None.

        Returns:
            List of paths to written files.
        """
        packs = packs if packs is not None else self.get_active_packs()
        output_dir.mkdir(parents=True, exist_ok=True)

        written: List[Path] = []
        ext = self.file_extension
        
        for name in self.list_names(packs):
            content = self.compose(name, packs)
            if content:
                output_path = output_dir / f"{name}{ext}"
                self.writer.write_text(output_path, content)
                written.append(output_path)

        return written


__all__ = ["GenericRegistry"]
