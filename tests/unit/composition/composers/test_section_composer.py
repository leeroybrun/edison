"""Tests for template composition with sections.

TDD: These tests define the expected behavior for the section composer.
The section composer uses the unified section system with HTML comment markers.
"""
from __future__ import annotations

from edison.core.composition import (
    SectionRegistry,
    SectionComposer,
)


class TestSectionComposer:
    """Tests for template composition with sections."""

    def test_compose_section_with_base_content(self) -> None:
        """Base section content should be included in output."""
        template = """# Agent: Test

<!-- SECTION: tools -->
- Base tool
<!-- /SECTION: tools -->

<!-- SECTION: guidelines -->
Base guideline
<!-- /SECTION: guidelines -->
"""
        registry = SectionRegistry(
            sections={
                "tools": ["- Extra Tool A", "- Extra Tool B"],
                "guidelines": ["Extra Guideline 1"],
            },
            extensions={},
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        # Base content from template section markers is replaced by registry content
        assert "- Extra Tool A" in result
        assert "- Extra Tool B" in result
        assert "Extra Guideline 1" in result

    def test_compose_with_extensions(self) -> None:
        """Extensions should be merged into section content."""
        template = """# Agent: Test

<!-- SECTION: tools -->
- Base tool
<!-- /SECTION: tools -->
"""
        registry = SectionRegistry(
            sections={
                "tools": ["- Base tool"],
            },
            extensions={
                "tools": ["- Extended tool from pack"],
            },
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        assert "- Base tool" in result
        assert "- Extended tool from pack" in result

    def test_compose_composed_additions_section(self) -> None:
        """Composed-additions section collects pack/project extensions."""
        template = """# Agent: Test

<!-- SECTION: composed-additions -->
<!-- /SECTION: composed-additions -->
"""
        registry = SectionRegistry(
            sections={
                "composed-additions": [],
            },
            extensions={
                "composed-additions": ["## Pack Content\nFrom pack A", "## More Content\nFrom pack B"],
            },
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        assert "From pack A" in result
        assert "From pack B" in result

    def test_compose_empty_sections_cleaned(self) -> None:
        """Empty sections should result in minimal output."""
        template = """# Agent: Test

<!-- SECTION: tools -->
<!-- /SECTION: tools -->

<!-- SECTION: composed-additions -->
<!-- /SECTION: composed-additions -->
"""
        registry = SectionRegistry(
            sections={"tools": [], "composed-additions": []},
            extensions={},
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        # No section markers should remain after composition
        assert "<!-- SECTION:" not in result
        assert "<!-- /SECTION:" not in result

    def test_compose_multiple_sections(self) -> None:
        """Multiple sections should all be processed."""
        template = """# Agent: Test

<!-- SECTION: tools -->
<!-- /SECTION: tools -->

<!-- SECTION: guidelines -->
<!-- /SECTION: guidelines -->

<!-- SECTION: patterns -->
<!-- /SECTION: patterns -->
"""
        registry = SectionRegistry(
            sections={
                "tools": ["Tool content"],
                "guidelines": ["Guideline content"],
                "patterns": ["Pattern content"],
            },
            extensions={},
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        assert "Tool content" in result
        assert "Guideline content" in result
        assert "Pattern content" in result
