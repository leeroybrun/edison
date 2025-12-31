"""Tests for simplified HTML comment section parsing.

TDD: These tests define the expected behavior for the unified section parser.
The simplified system uses only two patterns:
- <!-- SECTION: name --> content <!-- /SECTION: name -->
- <!-- EXTEND: name --> content <!-- /EXTEND -->

Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

import pytest

from edison.core.composition.core.sections import (
    SectionMode,
    SectionParser,
    SectionRegistry,
    ParsedSection,
)


# =============================================================================
# SectionParser Tests - Parsing SECTION markers
# =============================================================================


class TestParseSections:
    """Tests for parsing SECTION markers."""

    def test_parse_single_section(self) -> None:
        """Single SECTION should be parsed correctly."""
        content = """
<!-- SECTION: tools -->
- My custom tool
- Another tool
<!-- /SECTION: tools -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="core")

        assert len(sections) == 1
        assert sections[0].name == "tools"
        assert sections[0].mode == SectionMode.SECTION
        assert "My custom tool" in sections[0].content
        assert sections[0].source_layer == "core"

    def test_parse_multiple_sections(self) -> None:
        """Multiple SECTIONs should all be parsed."""
        content = """
<!-- SECTION: tools -->
Tool content
<!-- /SECTION: tools -->

<!-- SECTION: guidelines -->
Guideline content
<!-- /SECTION: guidelines -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="core")

        assert len(sections) == 2
        names = {s.name for s in sections}
        assert names == {"tools", "guidelines"}

    def test_parse_section_with_hyphen_in_name(self) -> None:
        """Section names with hyphens should be parsed."""
        content = """
<!-- SECTION: tech-stack -->
Framework specific content
<!-- /SECTION: tech-stack -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="core")

        assert len(sections) == 1
        assert sections[0].name == "tech-stack"

    def test_parse_empty_section(self) -> None:
        """Empty sections should be parsed correctly."""
        content = """
<!-- SECTION: composed-additions -->
<!-- /SECTION: composed-additions -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="core")

        assert len(sections) == 1
        assert sections[0].name == "composed-additions"
        assert sections[0].content == ""


# =============================================================================
# SectionParser Tests - Parsing EXTEND markers
# =============================================================================


class TestParseExtensions:
    """Tests for parsing EXTEND markers."""

    def test_parse_extend_section(self) -> None:
        """EXTEND comments should be parsed as extend mode."""
        content = """
<!-- EXTEND: tools -->
- Pack-specific tool
- Another tool
<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:fastify")

        assert len(sections) == 1
        assert sections[0].name == "tools"
        assert sections[0].mode == SectionMode.EXTEND
        assert "Pack-specific tool" in sections[0].content
        assert sections[0].source_layer == "pack:fastify"

    def test_parse_multiple_extend_sections(self) -> None:
        """Multiple EXTENDs should all be parsed."""
        content = """
<!-- EXTEND: tools -->
Tool extension
<!-- /EXTEND -->

<!-- EXTEND: guidelines -->
Guideline extension
<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:react")

        assert len(sections) == 2
        names = {s.name for s in sections}
        assert names == {"tools", "guidelines"}

    def test_parse_extend_with_hyphen_name(self) -> None:
        """EXTEND with hyphenated names should work."""
        content = """
<!-- EXTEND: composed-additions -->
## Pack-Specific Content
New content from pack
<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:vitest")

        assert len(sections) == 1
        assert sections[0].name == "composed-additions"


# =============================================================================
# SectionParser Tests - Mixed parsing
# =============================================================================


class TestParseMixed:
    """Tests for parsing mixed content."""

    def test_parse_mixed_sections_and_extends(self) -> None:
        """Both SECTION and EXTEND can be in one file."""
        content = """
<!-- SECTION: tools -->
Base tools content.
<!-- /SECTION: tools -->

<!-- EXTEND: guidelines -->
Extended guidelines.
<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:test")

        assert len(sections) == 2
        modes = {s.mode for s in sections}
        assert modes == {SectionMode.SECTION, SectionMode.EXTEND}

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
<!-- EXTEND: tools -->

  - Tool with whitespace

<!-- /EXTEND -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:test")

        assert len(sections) == 1
        # Content should be stripped
        assert sections[0].content == "- Tool with whitespace"


# =============================================================================
# SectionParser Tests - extract_section()
# =============================================================================


class TestExtractSection:
    """Tests for extract_section() method."""

    def test_extract_existing_section(self) -> None:
        """Extract content from existing section."""
        content = """
# Document

<!-- SECTION: tdd-rules -->
- Write tests first
- Tests must fail first
<!-- /SECTION: tdd-rules -->

Other content.
"""
        parser = SectionParser()
        result = parser.extract_section(content, "tdd-rules")

        assert result is not None
        assert "Write tests first" in result
        assert "Tests must fail first" in result

    def test_extract_missing_section(self) -> None:
        """Extract from non-existent section returns None."""
        content = """
<!-- SECTION: existing -->
Content
<!-- /SECTION: existing -->
"""
        parser = SectionParser()
        result = parser.extract_section(content, "nonexistent")

        assert result is None

    def test_extract_section_strips_content(self) -> None:
        """Extracted content should be stripped."""
        content = """
<!-- SECTION: test -->

  Content with whitespace

<!-- /SECTION: test -->
"""
        parser = SectionParser()
        result = parser.extract_section(content, "test")

        assert result == "Content with whitespace"


# =============================================================================
# SectionParser Tests - merge_extensions()
# =============================================================================


class TestMergeExtensions:
    """Tests for merge_extensions() method."""

    def test_merge_single_extension(self) -> None:
        """Merge one extension into a section."""
        base_content = """
<!-- section: tools -->
- Base tool
<!-- /section: tools -->
"""
        extensions = {"tools": ["- Extended tool"]}

        parser = SectionParser()
        result = parser.merge_extensions(base_content, extensions)

        assert "Base tool" in result
        assert "Extended tool" in result
        assert "<!-- section: tools -->" in result
        assert "<!-- /section: tools -->" in result

    def test_merge_multiple_extensions(self) -> None:
        """Merge multiple extensions into same section."""
        base_content = """
<!-- section: tools -->
- Base tool
<!-- /section: tools -->
"""
        extensions = {"tools": ["- Pack A tool", "- Pack B tool"]}

        parser = SectionParser()
        result = parser.merge_extensions(base_content, extensions)

        assert "Base tool" in result
        assert "Pack A tool" in result
        assert "Pack B tool" in result

    def test_merge_preserves_section_markers(self) -> None:
        """Markers should be preserved after merging."""
        base_content = """
<!-- section: composed-additions -->
<!-- /section: composed-additions -->
"""
        extensions = {"composed-additions": ["## New Section\nNew content"]}

        parser = SectionParser()
        result = parser.merge_extensions(base_content, extensions)

        assert "<!-- section: composed-additions -->" in result
        assert "<!-- /section: composed-additions -->" in result
        assert "## New Section" in result

    def test_merge_no_extensions(self) -> None:
        """No extensions returns original content."""
        base_content = """
<!-- section: tools -->
Content
<!-- /section: tools -->
"""
        parser = SectionParser()
        result = parser.merge_extensions(base_content, {})

        assert result == base_content

    def test_merge_unmatched_extension_ignored(self) -> None:
        """Extensions for non-existent sections are ignored."""
        base_content = """
<!-- section: tools -->
Content
<!-- /section: tools -->
"""
        extensions = {"nonexistent": ["Should be ignored"]}

        parser = SectionParser()
        result = parser.merge_extensions(base_content, extensions)

        assert "Should be ignored" not in result
        assert "Content" in result

    def test_merge_multiple_sections(self) -> None:
        """Extensions merged into correct sections."""
        base_content = """
<!-- SECTION: tools -->
Base tools
<!-- /SECTION: tools -->

<!-- SECTION: guidelines -->
Base guidelines
<!-- /SECTION: guidelines -->
"""
        extensions = {
            "tools": ["Extended tools"],
            "guidelines": ["Extended guidelines"],
        }

        parser = SectionParser()
        result = parser.merge_extensions(base_content, extensions)

        # Check tools section
        assert "Base tools" in result
        assert "Extended tools" in result

        # Check guidelines section
        assert "Base guidelines" in result
        assert "Extended guidelines" in result


# =============================================================================
# SectionParser Tests - strip_markers()
# =============================================================================


class TestStripMarkers:
    """Tests for strip_markers() method."""

    def test_strip_section_markers(self) -> None:
        """SECTION markers should be removed."""
        content = """
<!-- SECTION: tools -->
Content here
<!-- /SECTION: tools -->
"""
        parser = SectionParser()
        result = parser.strip_markers(content)

        assert "<!-- SECTION:" not in result
        assert "<!-- /SECTION:" not in result
        assert "Content here" in result

    def test_strip_extend_markers(self) -> None:
        """EXTEND markers should be removed."""
        content = """
<!-- EXTEND: tools -->
Extension content
<!-- /EXTEND -->
"""
        parser = SectionParser()
        result = parser.strip_markers(content)

        assert "<!-- EXTEND:" not in result
        assert "<!-- /EXTEND" not in result
        assert "Extension content" in result

    def test_strip_nested_section_markers(self) -> None:
        """Nested SECTION markers should be removed (iterate until stable)."""
        content = """
<!-- SECTION: outer -->
Outer start

<!-- SECTION: inner -->
Inner content
<!-- /SECTION: inner -->

Outer end
<!-- /SECTION: outer -->
"""
        parser = SectionParser()
        result = parser.strip_markers(content)

        assert "<!-- SECTION:" not in result.upper()
        assert "<!-- /SECTION:" not in result.upper()
        assert "Outer start" in result
        assert "Inner content" in result
        assert "Outer end" in result

    def test_strip_cleans_excessive_newlines(self) -> None:
        """Excessive newlines should be reduced."""
        content = """
Content



More content
"""
        parser = SectionParser()
        result = parser.strip_markers(content)

        assert "\n\n\n" not in result


# =============================================================================
# SectionRegistry Tests
# =============================================================================


class TestSectionRegistry:
    """Tests for SectionRegistry."""

    def test_add_section(self) -> None:
        """Adding sections should work."""
        registry = SectionRegistry()
        registry.add_section("tools", "Tool 1")
        registry.add_section("tools", "Tool 2")

        assert len(registry.sections["tools"]) == 2

    def test_add_extension(self) -> None:
        """Adding extensions should work."""
        registry = SectionRegistry()
        registry.add_extension("tools", "Extension 1")
        registry.add_extension("tools", "Extension 2")

        assert len(registry.extensions["tools"]) == 2

    def test_get_section_content_with_extensions(self) -> None:
        """Getting content should combine base and extensions."""
        registry = SectionRegistry()
        registry.add_section("tools", "Base tool")
        registry.add_extension("tools", "Extended tool")

        content = registry.get_section_content("tools")

        assert "Base tool" in content
        assert "Extended tool" in content

    def test_get_section_content_empty(self) -> None:
        """Getting non-existent section returns empty string."""
        registry = SectionRegistry()
        content = registry.get_section_content("nonexistent")

        assert content == ""


# =============================================================================
# Case Insensitivity Tests
# =============================================================================


class TestCaseInsensitivity:
    """Tests for case insensitivity in markers."""

    def test_section_case_insensitive(self) -> None:
        """SECTION markers should be case-insensitive."""
        content = """
<!-- section: tools -->
Content
<!-- /section: tools -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="core")

        assert len(sections) == 1
        assert sections[0].name == "tools"

    def test_extend_case_insensitive(self) -> None:
        """EXTEND markers should be case-insensitive."""
        content = """
<!-- extend: tools -->
Content
<!-- /extend -->
"""
        parser = SectionParser()
        sections = parser.parse(content, layer="pack:test")

        assert len(sections) == 1
        assert sections[0].mode == SectionMode.EXTEND
