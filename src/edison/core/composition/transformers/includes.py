"""Include transformers for template composition.

Handles:
- {{include:path}} - Include entire file
- {{include-optional:path}} - Include file if exists, empty string otherwise
- {{include-section:path#name}} - Extract and include a specific section
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, Set

from .base import ContentTransformer, TransformContext
from ..core.sections import SectionParser


class IncludeResolver(ContentTransformer):
    """Resolve {{include:path}} and {{include-optional:path}} directives.

    Includes are resolved from the source_dir in the context, with support
    for recursive includes up to a configurable max depth.
    """

    # Pattern for required includes: {{include:path}}
    INCLUDE_PATTERN = re.compile(r"\{\{include:([^}]+)\}\}")

    # Pattern for optional includes: {{include-optional:path}}
    INCLUDE_OPTIONAL_PATTERN = re.compile(r"\{\{include-optional:([^}]+)\}\}")

    def __init__(self, max_depth: int = 10) -> None:
        """Initialize with maximum recursion depth.

        Args:
            max_depth: Maximum depth for recursive includes (default 10)
        """
        self.max_depth = max_depth

    def transform(self, content: str, context: TransformContext) -> str:
        """Resolve all include directives in content.

        Args:
            content: Content with {{include:}} directives
            context: Transform context with source_dir

        Returns:
            Content with includes resolved
        """
        return self._resolve_includes(content, context, depth=0, seen=set())

    def _resolve_includes(
        self,
        content: str,
        context: TransformContext,
        depth: int,
        seen: Set[str],
    ) -> str:
        """Recursively resolve includes.

        Args:
            content: Content to process
            context: Transform context
            depth: Current recursion depth
            seen: Set of already-included paths (cycle detection)

        Returns:
            Content with includes resolved
        """
        if depth > self.max_depth:
            return content

        # Process required includes
        def replace_include(match: re.Match[str]) -> str:
            path = match.group(1).strip()
            return self._resolve_single_include(path, context, depth, seen, required=True)

        content = self.INCLUDE_PATTERN.sub(replace_include, content)

        # Process optional includes
        def replace_optional(match: re.Match[str]) -> str:
            path = match.group(1).strip()
            return self._resolve_single_include(path, context, depth, seen, required=False)

        content = self.INCLUDE_OPTIONAL_PATTERN.sub(replace_optional, content)

        return content

    def _resolve_single_include(
        self,
        path: str,
        context: TransformContext,
        depth: int,
        seen: Set[str],
        required: bool,
    ) -> str:
        """Resolve a single include path.

        Args:
            path: Relative path to include
            context: Transform context
            depth: Current recursion depth
            seen: Set of seen paths
            required: Whether the include is required

        Returns:
            File content or empty string (for optional) or error marker
        """
        # Cycle detection
        if path in seen:
            return f"<!-- ERROR: Circular include detected: {path} -->"

        # Resolve path
        full_path = self._resolve_path(path, context)

        if full_path is None or not full_path.exists():
            if required:
                return f"<!-- ERROR: Include not found: {path} -->"
            return ""

        # Read and recursively process
        try:
            included_content = full_path.read_text(encoding="utf-8")
            context.record_include(path)

            # Recursively resolve includes in included content
            new_seen = seen | {path}
            return self._resolve_includes(included_content, context, depth + 1, new_seen)

        except Exception as e:
            if required:
                return f"<!-- ERROR: Failed to include {path}: {e} -->"
            return ""

    def _resolve_path(self, path: str, context: TransformContext) -> Optional[Path]:
        """Resolve include path to absolute path.

        Searches in order:
        1. source_dir (composed files)
        2. project_root relative

        Args:
            path: Relative include path
            context: Transform context

        Returns:
            Resolved Path or None if not found
        """
        # Try source_dir first (for composed files)
        if context.source_dir:
            source_path = context.source_dir / path
            if source_path.exists():
                return source_path

        # Try project_root
        if context.project_root:
            project_path = context.project_root / path
            if project_path.exists():
                return project_path

        return None


class SectionExtractor(ContentTransformer):
    """Extract and include specific sections from files.

    Handles {{include-section:path#name}} directives.
    Extracts content between <!-- SECTION: name --> and <!-- /SECTION: name --> markers.
    """

    # Pattern for section includes: {{include-section:path#name}}
    INCLUDE_SECTION_PATTERN = re.compile(r"\{\{include-section:([^#]+)#([^}]+)\}\}")

    def __init__(self) -> None:
        """Initialize with section parser."""
        self.parser = SectionParser()

    def transform(self, content: str, context: TransformContext) -> str:
        """Process all {{include-section:path#name}} directives.

        Args:
            content: Content with section include directives
            context: Transform context with source_dir

        Returns:
            Content with section includes resolved
        """

        def replacer(match: re.Match[str]) -> str:
            file_path = match.group(1).strip()
            section_name = match.group(2).strip()
            return self._extract_section(file_path, section_name, context)

        return self.INCLUDE_SECTION_PATTERN.sub(replacer, content)

    def _extract_section(
        self,
        file_path: str,
        section_name: str,
        context: TransformContext,
    ) -> str:
        """Extract a section from a file.

        Args:
            file_path: Path to file containing the section
            section_name: Name of section to extract
            context: Transform context

        Returns:
            Section content or error marker
        """
        # Resolve file path
        full_path = self._resolve_path(file_path, context)

        if full_path is None or not full_path.exists():
            return f"<!-- ERROR: File not found for section extract: {file_path} -->"

        try:
            file_content = full_path.read_text(encoding="utf-8")
            section_content = self.parser.extract_section(file_content, section_name)

            if section_content is None:
                return f"<!-- ERROR: Section '{section_name}' not found in {file_path} -->"

            context.record_section_extract(file_path, section_name)
            return section_content

        except Exception as e:
            return f"<!-- ERROR: Failed to extract section {section_name} from {file_path}: {e} -->"

    def _resolve_path(self, path: str, context: TransformContext) -> Optional[Path]:
        """Resolve path to absolute path.

        Args:
            path: Relative path
            context: Transform context

        Returns:
            Resolved Path or None
        """
        # Try source_dir first (for composed files)
        if context.source_dir:
            source_path = context.source_dir / path
            if source_path.exists():
                return source_path

        # Try project_root
        if context.project_root:
            project_path = context.project_root / path
            if project_path.exists():
                return project_path

        return None


def resolve_single_include(
    path: str,
    source_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
    packs_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Resolve an include path using 3-layer search.

    Search order:
    1. source_dir (composed files)
    2. project_root relative
    3. packs_dir relative

    Args:
        path: Relative include path
        source_dir: Directory for composed files
        project_root: Project root directory
        packs_dir: Packs directory for pack-specific includes

    Returns:
        Resolved Path or None if not found
    """
    # Try source_dir first
    if source_dir:
        source_path = source_dir / path
        if source_path.exists():
            return source_path

    # Try project_root
    if project_root:
        project_path = project_root / path
        if project_path.exists():
            return project_path

    # Try packs_dir
    if packs_dir:
        packs_path = packs_dir / path
        if packs_path.exists():
            return packs_path

    return None


class IncludeTransformer(ContentTransformer):
    """Combined transformer for all include operations.

    Wraps IncludeResolver and SectionExtractor for use in the pipeline.
    Processes in order:
    1. Regular includes ({{include:}}, {{include-optional:}})
    2. Section extracts ({{include-section:}})
    """

    def __init__(self, max_include_depth: int = 10) -> None:
        """Initialize with sub-transformers.

        Args:
            max_include_depth: Maximum depth for recursive includes
        """
        self.include_resolver = IncludeResolver(max_depth=max_include_depth)
        self.section_extractor = SectionExtractor()

    def transform(self, content: str, context: TransformContext) -> str:
        """Process all include directives.

        Args:
            content: Content with include directives
            context: Transform context

        Returns:
            Content with all includes resolved
        """
        # First resolve file includes (they may contain section references)
        content = self.include_resolver.transform(content, context)

        # Then resolve section extracts
        content = self.section_extractor.transform(content, context)

        return content
