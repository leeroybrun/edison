"""Tests for section registry management.

TDD: These tests define the expected behavior for the unified section registry.
The registry now uses a simplified model with just sections and extensions.
"""
from __future__ import annotations

from edison.core.composition import SectionRegistry


class TestSectionRegistry:
    """Tests for section registry management."""

    def test_add_section(self) -> None:
        """Adding a section should create entry in sections dict."""
        registry = SectionRegistry(
            sections={"tools": []},
            extensions={},
        )

        registry.add_section("tools", "Tool content 1")
        registry.add_section("tools", "Tool content 2")

        assert len(registry.sections["tools"]) == 2
        assert "Tool content 1" in registry.sections["tools"]
        assert "Tool content 2" in registry.sections["tools"]

    def test_add_section_new_name(self) -> None:
        """Adding content to new section name creates the section."""
        registry = SectionRegistry(
            sections={},
            extensions={},
        )

        registry.add_section("architecture", "Arch content")

        assert "architecture" in registry.sections
        assert registry.sections["architecture"] == ["Arch content"]

    def test_add_extension(self) -> None:
        """Adding an extension should create entry in extensions dict."""
        registry = SectionRegistry(
            sections={"tools": []},
            extensions={},
        )

        registry.add_extension("tools", "Extension 1")
        registry.add_extension("tools", "Extension 2")

        assert len(registry.extensions["tools"]) == 2
        assert "Extension 1" in registry.extensions["tools"]
        assert "Extension 2" in registry.extensions["tools"]

    def test_add_extension_new_name(self) -> None:
        """Adding extension to new name creates the extensions entry."""
        registry = SectionRegistry(
            sections={},
            extensions={},
        )

        registry.add_extension("architecture", "Extension content")

        assert "architecture" in registry.extensions
        assert registry.extensions["architecture"] == ["Extension content"]

    def test_get_section_content_combines_base_and_extensions(self) -> None:
        """Getting section content should combine base and extensions."""
        registry = SectionRegistry(
            sections={"tools": ["Base tool"]},
            extensions={"tools": ["Extended tool"]},
        )

        content = registry.get_section_content("tools")

        assert "Base tool" in content
        assert "Extended tool" in content

    def test_get_section_content_empty(self) -> None:
        """Getting non-existent section returns empty string."""
        registry = SectionRegistry(
            sections={},
            extensions={},
        )

        content = registry.get_section_content("nonexistent")

        assert content == ""

    def test_get_section_content_only_sections(self) -> None:
        """Getting section with only base content works."""
        registry = SectionRegistry(
            sections={"tools": ["Tool 1", "Tool 2"]},
            extensions={},
        )

        content = registry.get_section_content("tools")

        assert "Tool 1" in content
        assert "Tool 2" in content

    def test_get_section_content_only_extensions(self) -> None:
        """Getting section with only extensions works."""
        registry = SectionRegistry(
            sections={},
            extensions={"tools": ["Extension 1"]},
        )

        content = registry.get_section_content("tools")

        assert "Extension 1" in content

    def test_registry_initialization(self) -> None:
        """Registry can be initialized with sections and extensions."""
        registry = SectionRegistry(
            sections={"tools": ["Tool"], "guidelines": ["Guide"]},
            extensions={"tools": ["Tool ext"]},
        )

        assert "tools" in registry.sections
        assert "guidelines" in registry.sections
        assert "tools" in registry.extensions
