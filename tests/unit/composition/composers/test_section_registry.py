"""Tests for section registry management.

TDD: These tests define the expected behavior for the section registry.
Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

import pytest

from edison.core.composition import (
    SectionRegistry,
    CompositionValidationError,
)


class TestSectionRegistry:
    """Tests for section registry management."""

    def test_add_extension_to_known_section(self) -> None:
        """Extending known section should add content."""
        registry = SectionRegistry(
            known_sections={"Tools": [], "Guidelines": []},
            extensible_sections={},
            append_sections=[],
        )

        registry.add_extension("Tools", "Tool from pack")
        registry.add_extension("Tools", "Another tool")

        assert len(registry.known_sections["Tools"]) == 2
        assert "Tool from pack" in registry.known_sections["Tools"]

    def test_add_extension_to_extensible_section(self) -> None:
        """Extending pack-defined section should add content."""
        registry = SectionRegistry(
            known_sections={"Tools": []},
            extensible_sections={"Architecture": ["Base arch"]},
            append_sections=[],
        )

        registry.add_extension("Architecture", "Project arch")

        assert len(registry.extensible_sections["Architecture"]) == 2

    def test_add_extension_to_unknown_section_raises(self) -> None:
        """Extending non-existent section should raise error."""
        registry = SectionRegistry(
            known_sections={"Tools": []},
            extensible_sections={},
            append_sections=[],
        )

        with pytest.raises(CompositionValidationError) as exc_info:
            registry.add_extension("NonExistent", "Content")

        assert "NonExistent" in str(exc_info.value)
        assert "not a known or extensible section" in str(exc_info.value)

    def test_add_new_section_creates_extensible(self) -> None:
        """NEW_SECTION should create new extensible section."""
        registry = SectionRegistry(
            known_sections={"Tools": []},
            extensible_sections={},
            append_sections=[],
        )

        registry.add_new_section("Architecture", "Arch content")

        assert "Architecture" in registry.extensible_sections
        assert registry.extensible_sections["Architecture"] == ["Arch content"]

    def test_add_new_section_can_be_extended(self) -> None:
        """NEW_SECTION can be extended by later layers."""
        registry = SectionRegistry(
            known_sections={},
            extensible_sections={},
            append_sections=[],
        )

        # Pack A creates new section
        registry.add_new_section("Architecture", "Pack A arch")

        # Pack B extends it
        registry.add_extension("Architecture", "Pack B additions")

        # Project extends it
        registry.add_extension("Architecture", "Project additions")

        assert len(registry.extensible_sections["Architecture"]) == 3

    def test_add_new_section_shadowing_known_raises(self) -> None:
        """Creating new section that shadows known section should raise."""
        registry = SectionRegistry(
            known_sections={"Tools": []},
            extensible_sections={},
            append_sections=[],
        )

        with pytest.raises(CompositionValidationError) as exc_info:
            registry.add_new_section("Tools", "Content")

        assert "Tools" in str(exc_info.value)
        assert "already a known section" in str(exc_info.value)

    def test_add_append_content(self) -> None:
        """APPEND content should be added to catch-all."""
        registry = SectionRegistry(
            known_sections={},
            extensible_sections={},
            append_sections=[],
        )

        registry.add_append("Random content 1")
        registry.add_append("Random content 2")

        assert len(registry.append_sections) == 2
