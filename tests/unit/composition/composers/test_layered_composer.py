"""Tests for the unified layered composer.

TDD: These tests define the expected behavior for the layered composer.
The composer uses the unified section system with HTML comment markers.

Architecture:
- Core content: ALWAYS from bundled edison.data package
- Pack overlays: At .edison/packs/{pack}/{type}/overlays/{name}.md
- Project overlays: At .edison/{type}/overlays/{name}.md
- NO .edison/core/ - that is LEGACY
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition import (
    LayeredComposer,
    CompositionValidationError,
)
from edison.core.utils.paths.project import get_project_config_dir


class TestLayeredComposerCoreDiscovery:
    """Tests for core entity discovery from bundled data."""

    def test_discover_core_entities_from_bundled_data(self, isolated_project_env: Path) -> None:
        """Should discover core entities from bundled edison.data package."""
        root = isolated_project_env

        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()

        # Should find bundled core agents
        assert "api-builder" in core
        assert "code-reviewer" in core
        assert "feature-implementer" in core
        assert core["api-builder"].layer == "core"

    def test_core_dir_is_bundled_data(self, isolated_project_env: Path) -> None:
        """Core directory should be bundled edison.data, NOT .edison/core/."""
        root = isolated_project_env
        
        composer = LayeredComposer(repo_root=root, content_type="agents")
        
        # Core dir should NOT be project-local
        assert ".edison" not in str(composer.core_dir)
        # Core dir should be in the bundled package
        assert "edison" in str(composer.core_dir) and "data" in str(composer.core_dir)


class TestLayeredComposerPackOverlays:
    """Tests for pack overlay discovery and composition."""

    def test_discover_pack_overlays_for_existing_entity(self, isolated_project_env: Path) -> None:
        """Should discover pack overlays in overlays/ subfolder."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create pack overlay for existing bundled agent
        pack_overlays = project_dir / "packs" / "fastify" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "api-builder.md").write_text(
            "<!-- EXTEND: tools -->\n- Fastify route handlers\n<!-- /EXTEND -->"
        )

        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()
        overlays = composer.discover_pack_overlays("fastify", set(core.keys()))

        assert "api-builder" in overlays
        assert overlays["api-builder"].is_overlay
        assert overlays["api-builder"].layer == "pack:fastify"

    def test_pack_overlay_for_nonexistent_entity_raises(self, isolated_project_env: Path) -> None:
        """Pack overlay for non-existent entity should raise error."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create pack overlay for non-existent agent
        pack_overlays = project_dir / "packs" / "react" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "nonexistent-agent.md").write_text("<!-- EXTEND: tools -->")

        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()

        with pytest.raises(CompositionValidationError) as exc_info:
            composer.discover_pack_overlays("react", existing=set(core.keys()))

        assert "nonexistent-agent" in str(exc_info.value)
        assert "non-existent" in str(exc_info.value).lower()


class TestLayeredComposerPackNewEntities:
    """Tests for pack-defined new entities."""

    def test_discover_pack_new_entities(self, isolated_project_env: Path) -> None:
        """Should discover new pack-defined entities in root folder."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create pack-specific agent (new, not overlay)
        pack_agents = project_dir / "packs" / "react" / "agents"
        pack_agents.mkdir(parents=True, exist_ok=True)
        (pack_agents / "react-specialist.md").write_text("# Agent: react-specialist")

        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()
        new_entities = composer.discover_pack_new("react", existing=set(core.keys()))

        assert "react-specialist" in new_entities
        assert not new_entities["react-specialist"].is_overlay

    def test_pack_new_shadowing_core_raises(self, isolated_project_env: Path) -> None:
        """Pack new entity shadowing core entity should raise error."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Try to create pack agent with same name as bundled core agent
        pack_agents = project_dir / "packs" / "react" / "agents"
        pack_agents.mkdir(parents=True, exist_ok=True)
        (pack_agents / "api-builder.md").write_text("# Agent: api-builder (pack)")

        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()

        with pytest.raises(CompositionValidationError) as exc_info:
            composer.discover_pack_new("react", existing=set(core.keys()))

        assert "api-builder" in str(exc_info.value)
        assert "shadows" in str(exc_info.value).lower()


class TestLayeredComposerProjectOverlays:
    """Tests for project-level overlays."""

    def test_discover_project_overlays(self, isolated_project_env: Path) -> None:
        """Should discover project overlays for existing entities."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create project overlay for bundled agent
        proj_overlays = project_dir / "agents" / "overlays"
        proj_overlays.mkdir(parents=True, exist_ok=True)
        (proj_overlays / "api-builder.md").write_text(
            "<!-- EXTEND: composed-additions -->\n## Project Notes\n<!-- /EXTEND -->"
        )

        composer = LayeredComposer(repo_root=root, content_type="agents")
        core = composer.discover_core()
        project_overlays = composer.discover_project_overlays(set(core.keys()))

        assert "api-builder" in project_overlays
        assert project_overlays["api-builder"].is_overlay


class TestLayeredComposerComposition:
    """Tests for full composition workflow."""

    def test_compose_bundled_agent_with_pack_overlay(self, isolated_project_env: Path) -> None:
        """Compose bundled agent with pack overlay extensions."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create pack overlay with tool extensions
        pack_overlays = project_dir / "packs" / "fastify" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "api-builder.md").write_text("""
<!-- EXTEND: tools -->
- Fastify route handlers
- Fastify schema validation
<!-- /EXTEND -->

<!-- EXTEND: guidelines -->
Follow Fastify plugin patterns.
<!-- /EXTEND -->
""")

        composer = LayeredComposer(repo_root=root, content_type="agents")
        result = composer.compose("api-builder", packs=["fastify"])

        # Original bundled content should be present
        assert "Backend API specialist" in result or "api-builder" in result.lower()
        # Pack extensions should be merged
        assert "Fastify route handlers" in result
        assert "Fastify schema validation" in result
        assert "Fastify plugin patterns" in result

    def test_compose_bundled_agent_with_project_overlay(self, isolated_project_env: Path) -> None:
        """Compose bundled agent with project overlay extensions."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create project overlay
        proj_overlays = project_dir / "agents" / "overlays"
        proj_overlays.mkdir(parents=True, exist_ok=True)
        (proj_overlays / "api-builder.md").write_text("""
<!-- EXTEND: composed-additions -->
## Project-Specific API Standards

Our API follows company-specific conventions.
<!-- /EXTEND -->
""")

        composer = LayeredComposer(repo_root=root, content_type="agents")
        result = composer.compose("api-builder", packs=[])

        # Project overlay content should be present
        assert "Project-Specific API Standards" in result
        assert "company-specific conventions" in result

    def test_compose_with_pack_and_project_overlays(self, isolated_project_env: Path) -> None:
        """Full composition: bundled core + pack overlay + project overlay."""
        root = isolated_project_env
        project_dir = get_project_config_dir(root, create=True)

        # Create pack overlay
        pack_overlays = project_dir / "packs" / "fastify" / "agents" / "overlays"
        pack_overlays.mkdir(parents=True, exist_ok=True)
        (pack_overlays / "api-builder.md").write_text("""
<!-- EXTEND: tools -->
- Fastify routing
<!-- /EXTEND -->
""")

        # Create project overlay
        proj_overlays = project_dir / "agents" / "overlays"
        proj_overlays.mkdir(parents=True, exist_ok=True)
        (proj_overlays / "api-builder.md").write_text("""
<!-- EXTEND: tools -->
- Company logging library
<!-- /EXTEND -->

<!-- EXTEND: composed-additions -->
## Team Standards
Use our internal SDK.
<!-- /EXTEND -->
""")

        composer = LayeredComposer(repo_root=root, content_type="agents")
        result = composer.compose("api-builder", packs=["fastify"])

        # All content should be merged in order: core -> pack -> project
        assert "Fastify routing" in result
        assert "Company logging library" in result
        assert "Team Standards" in result

    def test_compose_nonexistent_agent_raises(self, isolated_project_env: Path) -> None:
        """Composing non-existent agent should raise error."""
        root = isolated_project_env

        composer = LayeredComposer(repo_root=root, content_type="agents")

        with pytest.raises(CompositionValidationError) as exc_info:
            composer.compose("nonexistent-agent", packs=[])

        assert "nonexistent-agent" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()
