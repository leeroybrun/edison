"""Tests for the unified layered composer.

TDD: These tests define the expected behavior for the layered composer.
Write tests first (RED), then implement (GREEN), then refactor.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition import (
    LayeredComposer,
    CompositionValidationError,
)
from edison.core.utils.paths.project import get_project_config_dir


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
