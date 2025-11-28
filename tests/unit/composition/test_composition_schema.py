"""Tests for composition schema loading.

TDD: These tests define the expected behavior for the composition schema.
Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import CompositionSchema


class TestCompositionSchema:
    """Tests for composition schema loading."""

    def test_load_schema_from_yaml(self, isolated_project_env: Path) -> None:
        """Schema should be loadable from composition.yaml."""
        schema = CompositionSchema.load()

        assert schema.version == "1.0"
        assert "agents" in schema.content_types
        assert "validators" in schema.content_types
        assert "guidelines" in schema.content_types

    def test_get_known_sections_for_type(self) -> None:
        """Should return known sections for a content type."""
        schema = CompositionSchema.load()

        agent_sections = schema.get_known_sections("agents")
        assert "Tools" in agent_sections
        assert "Guidelines" in agent_sections

    def test_get_placeholder_for_section(self) -> None:
        """Should return correct placeholder for a section."""
        schema = CompositionSchema.load()

        placeholder = schema.get_placeholder("agents", "Tools")
        assert placeholder == "{{SECTION:Tools}}"
