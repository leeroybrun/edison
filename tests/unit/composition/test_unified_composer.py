"""Tests for unified layered composition system.

TDD: These tests define the expected behavior for the unified composition engine.
Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Dict, List, Set

from edison.core.composition import (
    SectionMode,
    ParsedSection,
    SectionParser,
    SectionRegistry,
    SectionComposer,
    LayeredComposer,
    CompositionSchema,
    CompositionValidationError,
)
from edison.core.paths.project import get_project_config_dir


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


class TestLayeredComposer:
    """Tests for the unified layered composer."""
    
    def test_discover_core_entities(self, isolated_project_env: Path) -> None:
        """Should discover core entity definitions."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)
        
        # Create core agent
        core_agents = project_dir / "core" / "agents"
        core_agents.mkdir(parents=True, exist_ok=True)
        (core_agents / "test-agent.md").write_text("# Agent: test-agent\n## Role\nTest role.")
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()
        
        assert "test-agent" in core
        assert core["test-agent"].layer == "core"
    
    def test_discover_pack_overlays(self, isolated_project_env: Path) -> None:
        """Should discover pack overlays in overlays/ subfolder."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)
        
        # Create core agent (required for overlay to be valid)
        core_agents = project_dir / "core" / "agents"
        core_agents.mkdir(parents=True, exist_ok=True)
        (core_agents / "test-agent.md").write_text("# Agent: test-agent")
        
        # Create pack overlay
        pack_overlays = project_dir / "packs" / "react" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "test-agent.md").write_text("<!-- EXTEND: Tools -->\nReact tools\n<!-- /EXTEND -->")
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()
        overlays = composer.discover_pack_overlays("react", set(core.keys()))
        
        assert "test-agent" in overlays
        assert overlays["test-agent"].is_overlay
        assert overlays["test-agent"].layer == "pack:react"
    
    def test_pack_overlay_for_nonexistent_core_raises(self, isolated_project_env: Path) -> None:
        """Pack overlay for non-existent core entity should raise error."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)
        
        # Create pack overlay WITHOUT corresponding core agent
        pack_overlays = project_dir / "packs" / "react" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "nonexistent-agent.md").write_text("<!-- EXTEND: Tools -->")
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        
        with pytest.raises(CompositionValidationError) as exc_info:
            composer.discover_pack_overlays("react", existing=set())
        
        assert "nonexistent-agent" in str(exc_info.value)
        assert "non-existent" in str(exc_info.value).lower()
    
    def test_discover_pack_new_entities(self, isolated_project_env: Path) -> None:
        """Should discover new pack-defined entities in root folder."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)
        
        # Create pack-specific agent (new, not overlay)
        pack_agents = project_dir / "packs" / "react" / "agents"
        pack_agents.mkdir(parents=True, exist_ok=True)
        (pack_agents / "react-specialist.md").write_text("# Agent: react-specialist")
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        new_entities = composer.discover_pack_new("react", existing=set())
        
        assert "react-specialist" in new_entities
        assert not new_entities["react-specialist"].is_overlay
    
    def test_pack_new_shadowing_core_raises(self, isolated_project_env: Path) -> None:
        """Pack new entity shadowing core entity should raise error."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)
        
        # Create core agent
        core_agents = project_dir / "core" / "agents"
        core_agents.mkdir(parents=True, exist_ok=True)
        (core_agents / "test-agent.md").write_text("# Agent: test-agent")
        
        # Try to create pack agent with same name (shadowing)
        pack_agents = project_dir / "packs" / "react" / "agents"
        pack_agents.mkdir(parents=True, exist_ok=True)
        (pack_agents / "test-agent.md").write_text("# Agent: test-agent (pack)")
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()
        
        with pytest.raises(CompositionValidationError) as exc_info:
            composer.discover_pack_new("react", existing=set(core.keys()))
        
        assert "test-agent" in str(exc_info.value)
        assert "shadows" in str(exc_info.value).lower()
    
    def test_compose_full_agent(self, isolated_project_env: Path) -> None:
        """Full agent composition with core + packs + project."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)
        
        # Create core agent with placeholders
        core_agents = project_dir / "core" / "agents"
        core_agents.mkdir(parents=True, exist_ok=True)
        (core_agents / "api-builder.md").write_text("""# Agent: api-builder

## Role
Backend API specialist.

## Tools
{{SECTION:Tools}}

## Guidelines
{{SECTION:Guidelines}}

{{EXTENSIBLE_SECTIONS}}

{{APPEND_SECTIONS}}
""")
        
        # Create pack overlay
        pack_overlays = project_dir / "packs" / "fastify" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "api-builder.md").write_text("""
<!-- EXTEND: Tools -->
- Fastify route handlers
- Schema validation
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
Follow Fastify plugin patterns.
<!-- /EXTEND -->

<!-- NEW_SECTION: PackPatterns -->
## Pack Patterns
Fastify-specific patterns (pack-defined extensible section).
<!-- /NEW_SECTION -->
""")
        
        # Create project overlay
        proj_overlays = project_dir / "agents" / "overlays"
        proj_overlays.mkdir(parents=True, exist_ok=True)
        (proj_overlays / "api-builder.md").write_text("""
<!-- EXTEND: Tools -->
- Project-specific tools
<!-- /EXTEND -->

<!-- EXTEND: PackPatterns -->
Project additions to pack-defined section.
<!-- /EXTEND -->

<!-- APPEND -->
## Project Notes
Custom notes.
<!-- /APPEND -->
""")
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        result = composer.compose("api-builder", packs=["fastify"])
        
        # All content should be present
        assert "Backend API specialist" in result
        assert "Fastify route handlers" in result
        assert "Project-specific tools" in result
        assert "Follow Fastify plugin patterns" in result
        assert "Fastify-specific patterns" in result  # Pack-defined NEW_SECTION
        assert "Project additions to pack-defined section" in result  # Project extends pack's section
        assert "Project Notes" in result
        assert "Custom notes" in result
        
        # No placeholders should remain
        assert "{{SECTION:" not in result
        assert "{{EXTENSIBLE_SECTIONS}}" not in result
        assert "{{APPEND_SECTIONS}}" not in result

