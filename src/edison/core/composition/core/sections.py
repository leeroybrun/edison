"""Section parsing and registry for layered composition.

Unified section system with two core patterns:
- <!-- section: name --> content <!-- /section: name -->  (Define section)
- <!-- extend: name --> content <!-- /extend -->  (Extend existing section)

Convention: `composed-additions` section for pack/project new content.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .errors import CompositionValidationError


class SectionMode(Enum):
    """Mode for section handling in overlays."""

    SECTION = "section"  # Define a named section (extensible + extractable)
    EXTEND = "extend"  # Extend an existing section


@dataclass
class ParsedSection:
    """A parsed section from a content file."""

    name: str
    mode: SectionMode
    content: str
    source_layer: str  # "core" | "pack:{name}" | "project"


@dataclass
class SectionRegistry:
    """Registry managing sections across composition layers.

    Tracks:
    - sections: Named sections that can be extended and extracted
    - extensions: Content to be added to existing sections
    """

    sections: Dict[str, List[str]] = field(default_factory=dict)
    extensions: Dict[str, List[str]] = field(default_factory=dict)

    def add_section(self, name: str, content: str) -> None:
        """Define or add to a named section."""
        if name not in self.sections:
            self.sections[name] = []
        self.sections[name].append(content)

    def add_extension(self, name: str, content: str) -> None:
        """Add extension content for a section.

        Extensions are merged into sections during composition.
        """
        if name not in self.extensions:
            self.extensions[name] = []
        self.extensions[name].append(content)

    def get_section_content(self, name: str) -> str:
        """Get composed content for a section (base + extensions)."""
        base_content = "\n\n".join(self.sections.get(name, []))
        ext_content = "\n\n".join(self.extensions.get(name, []))

        if base_content and ext_content:
            return f"{base_content}\n{ext_content}"
        return base_content or ext_content


class SectionParser:
    """Parse HTML comment markers in content files.

    Supported markers:
    - <!-- section: name --> content <!-- /section: name -->
    - <!-- extend: name --> content <!-- /extend -->
    """

    # Optional comment prefixes for non-markdown content types (e.g. scripts).
    #
    # Examples:
    #   # <!-- SECTION: body -->
    #   // <!-- SECTION: body -->
    #
    # The prefix is intentionally optional so inline markers like:
    #   <!-- SECTION: role -->Base<!-- /SECTION: role -->
    # continue to work.
    _OPTIONAL_LINE_PREFIX = r"(?:^[ \t]*(?:(?:#|//|--|;)\s*)?)?"

    # Pattern for section definitions (supports dots for rule IDs like RULE.SESSION.ISOLATION)
    SECTION_PATTERN = re.compile(
        rf"{_OPTIONAL_LINE_PREFIX}<!--\s*SECTION:\s*([\w.-]+)\s*-->(.*?){_OPTIONAL_LINE_PREFIX}<!--\s*/SECTION:\s*\1\s*-->",
        re.DOTALL | re.IGNORECASE | re.MULTILINE,
    )

    # Pattern for section extensions
    EXTEND_PATTERN = re.compile(
        rf"{_OPTIONAL_LINE_PREFIX}<!--\s*EXTEND:\s*([\w.-]+)\s*-->(.*?){_OPTIONAL_LINE_PREFIX}<!--\s*/EXTEND\s*-->",
        re.DOTALL | re.IGNORECASE | re.MULTILINE,
    )

    def parse(self, content: str, layer: str = "unknown") -> List[ParsedSection]:
        """Parse content into structured sections."""
        sections: List[ParsedSection] = []

        # Parse SECTION definitions
        for match in self.SECTION_PATTERN.finditer(content):
            sections.append(
                ParsedSection(
                    name=match.group(1),
                    mode=SectionMode.SECTION,
                    content=match.group(2).strip(),
                    source_layer=layer,
                )
            )

        # Parse EXTEND sections
        for match in self.EXTEND_PATTERN.finditer(content):
            sections.append(
                ParsedSection(
                    name=match.group(1),
                    mode=SectionMode.EXTEND,
                    content=match.group(2).strip(),
                    source_layer=layer,
                )
            )

        return sections

    def parse_sections(self, content: str) -> Dict[str, str]:
        """Parse and return a dict of section name -> content."""
        result: Dict[str, str] = {}
        for match in self.SECTION_PATTERN.finditer(content):
            result[match.group(1)] = match.group(2).strip()
        return result

    def parse_extensions(self, content: str) -> Dict[str, List[str]]:
        """Parse and return a dict of section name -> list of extension content."""
        result: Dict[str, List[str]] = {}
        for match in self.EXTEND_PATTERN.finditer(content):
            name = match.group(1)
            if name not in result:
                result[name] = []
            result[name].append(match.group(2).strip())
        return result

    def extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a specific section's content from composed content.

        Args:
            content: Content containing section markers
            section_name: Name of the section to extract

        Returns:
            Section content or None if not found
        """
        pattern = re.compile(
            rf"{self._OPTIONAL_LINE_PREFIX}<!--\s*SECTION:\s*{re.escape(section_name)}\s*-->(.*?){self._OPTIONAL_LINE_PREFIX}<!--\s*/SECTION:\s*{re.escape(section_name)}\s*-->",
            re.DOTALL | re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        return None

    def merge_extensions(
        self,
        content: str,
        extensions: Dict[str, List[str]],
    ) -> str:
        """Merge EXTEND content into SECTION regions.

        Args:
            content: Base content with SECTION markers
            extensions: Dict mapping section names to list of extension content

        Returns:
            Content with extensions merged into sections
        """

        def replacer(match: re.Match[str]) -> str:
            section_name = match.group(1)
            section_content = match.group(2)

            if section_name in extensions:
                # Append extension content before closing marker
                extended = section_content.rstrip()
                for ext in extensions[section_name]:
                    if ext:  # Skip empty extensions
                        extended += "\n" + ext
                return f"<!-- section: {section_name} -->{extended}\n<!-- /section: {section_name} -->"

            return match.group(0)

        return self.SECTION_PATTERN.sub(replacer, content)

    def strip_markers(self, content: str) -> str:
        """Remove all section markers from content, keeping only the content.

        Useful for final output where markers should not be visible.
        """
        # Replace SECTION/EXTEND markers, keeping inner content.
        #
        # NOTE: SECTION blocks can be nested (e.g., a rule section that contains
        # a more specific sub-section). A single pass won't strip inner markers
        # because `re.sub` doesn't re-scan replacements. Iterate until stable.
        result = content
        for _ in range(50):
            prev = result
            result = self.SECTION_PATTERN.sub(r"\2", result)
            result = self.EXTEND_PATTERN.sub(r"\2", result)
            if result == prev:
                break
        # Clean up excessive blank lines
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()
