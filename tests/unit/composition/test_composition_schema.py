"""Tests for composition schema loading.

TDD: These tests define the expected behavior for the composition schema.
The unified 4-concept section system uses:
- SECTION markers: <!-- SECTION: name -->...<!-- /SECTION: name -->
- EXTEND markers: <!-- EXTEND: name -->...<!-- /EXTEND -->
- No more placeholder syntax ({{SECTION:Name}}, {{EXTENSIBLE_SECTIONS}}, etc.)
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import CompositionSchema


class TestCompositionSchema:
    """Tests for composition schema loading."""

    def test_load_schema_from_yaml(self, isolated_project_env: Path) -> None:
        """Schema should be loadable from composition.yaml."""
        CompositionSchema.reset_cache()
        schema = CompositionSchema.load()

        assert schema.version == "2.0"
        assert "agents" in schema.content_types
        assert "validators" in schema.content_types
        assert "guidelines" in schema.content_types

    def test_get_known_sections_for_type(self) -> None:
        """Should return known sections for a content type.
        
        Note: Section names are now lowercase (unified syntax).
        """
        CompositionSchema.reset_cache()
        schema = CompositionSchema.load()

        agent_sections = schema.get_known_sections("agents")
        # Section names are now lowercase
        assert "tools" in agent_sections
        assert "guidelines" in agent_sections
        assert "composed-additions" in agent_sections

    def test_is_section_extensible(self) -> None:
        """Should correctly identify extensible sections.
        
        Replaced get_placeholder test - placeholders are deprecated.
        Now we test the is_section_extensible method instead.
        """
        CompositionSchema.reset_cache()
        schema = CompositionSchema.load()

        # 'tools' is mode: append, so extensible
        assert schema.is_section_extensible("agents", "tools") is True
        # 'role' is mode: replace, so not extensible
        assert schema.is_section_extensible("agents", "role") is False
        # 'composed-additions' is always extensible
        assert schema.is_section_extensible("agents", "composed-additions") is True

    def test_content_type_has_known_sections(self) -> None:
        """Content types should have SectionSchema objects."""
        CompositionSchema.reset_cache()
        schema = CompositionSchema.load()

        agents_schema = schema.get_content_type("agents")
        assert len(agents_schema.known_sections) > 0
        
        # Each section should have name, mode, description
        for section in agents_schema.known_sections:
            assert hasattr(section, "name")
            assert hasattr(section, "mode")
            assert hasattr(section, "description")
            assert section.mode in ("replace", "append")

    def test_no_deprecated_placeholder_fields(self) -> None:
        """Schema should NOT have deprecated placeholder fields."""
        CompositionSchema.reset_cache()
        schema = CompositionSchema.load()

        for name, ct in schema.content_types.items():
            # These fields should NOT exist (deprecated)
            assert not hasattr(ct, "extensible_placeholder"), \
                f"{name} should not have extensible_placeholder"
            assert not hasattr(ct, "append_placeholder"), \
                f"{name} should not have append_placeholder"
