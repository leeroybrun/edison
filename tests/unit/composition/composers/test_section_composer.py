"""Tests for template composition with sections.

TDD: These tests define the expected behavior for the section composer.
Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

from edison.core.composition import (
    SectionRegistry,
    SectionComposer,
)


class TestSectionComposer:
    """Tests for template composition with sections."""

    def test_compose_known_sections(self) -> None:
        """Known sections should be substituted at placeholders."""
        template = """# Agent: Test

## Tools
{{SECTION:Tools}}

## Guidelines
{{SECTION:Guidelines}}
"""
        registry = SectionRegistry(
            known_sections={
                "Tools": ["- Tool A", "- Tool B"],
                "Guidelines": ["Guideline 1"],
            },
            extensible_sections={},
            append_sections=[],
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        assert "- Tool A" in result
        assert "- Tool B" in result
        assert "Guideline 1" in result
        assert "{{SECTION:" not in result  # All placeholders replaced

    def test_compose_extensible_sections(self) -> None:
        """Extensible sections should be rendered at placeholder."""
        template = """# Agent: Test

{{EXTENSIBLE_SECTIONS}}
"""
        registry = SectionRegistry(
            known_sections={},
            extensible_sections={
                "Architecture": ["Arch from pack A", "Arch from pack B"],
                "Security": ["Security content"],
            },
            append_sections=[],
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        assert "Arch from pack A" in result
        assert "Arch from pack B" in result
        assert "Security content" in result
        assert "{{EXTENSIBLE_SECTIONS}}" not in result

    def test_compose_append_sections(self) -> None:
        """Append sections should be rendered at placeholder."""
        template = """# Agent: Test

{{APPEND_SECTIONS}}
"""
        registry = SectionRegistry(
            known_sections={},
            extensible_sections={},
            append_sections=["## Custom Notes\nContent 1", "Content 2"],
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        assert "Custom Notes" in result
        assert "Content 1" in result
        assert "Content 2" in result

    def test_compose_empty_sections_cleaned(self) -> None:
        """Empty section placeholders should be cleaned up."""
        template = """# Agent: Test

## Tools
{{SECTION:Tools}}

{{EXTENSIBLE_SECTIONS}}

{{APPEND_SECTIONS}}
"""
        registry = SectionRegistry(
            known_sections={"Tools": []},
            extensible_sections={},
            append_sections=[],
        )

        composer = SectionComposer()
        result = composer.compose(template, registry)

        # No placeholders should remain
        assert "{{SECTION:" not in result
        assert "{{EXTENSIBLE_SECTIONS}}" not in result
        assert "{{APPEND_SECTIONS}}" not in result
