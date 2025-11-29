"""Tests for HTML comment section parsing.

TDD: These tests define the expected behavior for the section parser.
Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

import pytest

from edison.core.composition import (
    SectionMode,
    SectionParser,
)


class TestSectionParser:
    """Tests for HTML comment section parsing."""

    def test_parse_extend_section(self) -> None:
        """EXTEND comments should be parsed as extend mode."""
        content = """
<!-- EXTEND: Tools -->
- My custom tool
- Another tool
<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:fastify")

        assert len(sections) == 1
        assert sections[0].name == "Tools"
        assert sections[0].mode == SectionMode.EXTEND
        assert "My custom tool" in sections[0].content
        assert sections[0].source_layer == "pack:fastify"

    def test_parse_multiple_extend_sections(self) -> None:
        """Multiple EXTEND sections should all be parsed."""
        content = """
<!-- EXTEND: Tools -->
Tool content
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
Guideline content
<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:react")

        assert len(sections) == 2
        names = {s.name for s in sections}
        assert names == {"Tools", "Guidelines"}

    def test_parse_new_section(self) -> None:
        """NEW_SECTION comments should create extensible sections."""
        content = """
<!-- NEW_SECTION: Architecture -->
## Architecture
Pack-specific architecture patterns.
<!-- /NEW_SECTION -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:fastify")

        assert len(sections) == 1
        assert sections[0].name == "Architecture"
        assert sections[0].mode == SectionMode.NEW_SECTION
        assert "Pack-specific architecture" in sections[0].content

    def test_parse_append_section(self) -> None:
        """APPEND comments should be parsed as catch-all."""
        content = """
<!-- APPEND -->
## Custom Notes
Random project-specific content.
<!-- /APPEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="project")

        assert len(sections) == 1
        assert sections[0].name == "_append"
        assert sections[0].mode == SectionMode.APPEND
        assert "Custom Notes" in sections[0].content

    def test_parse_mixed_sections(self) -> None:
        """All section types can be mixed in one file."""
        content = """
<!-- EXTEND: Tools -->
Extended tools.
<!-- /EXTEND -->

<!-- NEW_SECTION: Security -->
## Security
Security section.
<!-- /NEW_SECTION -->

<!-- APPEND -->
Catch-all content.
<!-- /APPEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:auth")

        assert len(sections) == 3
        modes = {s.mode for s in sections}
        assert modes == {SectionMode.EXTEND, SectionMode.NEW_SECTION, SectionMode.APPEND}

    def test_parse_empty_content_returns_empty_list(self) -> None:
        """Empty content should return empty list."""
        parser = SectionParser()
        sections = parser.parse("", layer="core")
        assert sections == []

    def test_parse_no_markers_returns_empty_list(self) -> None:
        """Content without markers returns empty list."""
        content = "Just some plain markdown without any markers."
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:test")
        assert sections == []

    def test_parse_whitespace_handling(self) -> None:
        """Content should be trimmed of leading/trailing whitespace."""
        content = """
<!-- EXTEND: Tools -->

  - Tool with whitespace

<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:test")

        assert len(sections) == 1
        # Content should be stripped
        assert sections[0].content == "- Tool with whitespace"
