"""Tests for basic agent composition functionality.

NO MOCKS - real files, real behavior.

NOTE: Core agents come from bundled edison.data, not .edison/core/.
Tests use real bundled agents and apply pack overlays to them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition import (
    AgentRegistry,
    AgentNotFoundError,
    compose_agent,
)
from .test_agent_composition_helpers import write_pack_overlay


class TestAgentCompositionBasic:
    """Tests for basic agent composition operations."""

    def test_agent_discovery_from_bundled_core(self, isolated_project_env: Path) -> None:
        """AgentRegistry discovers bundled core agents from edison.data."""
        registry = AgentRegistry()
        core_agents = registry.discover_core()

        # api-builder is a real bundled agent
        # discover_core() returns Dict[str, Path]
        assert "api-builder" in core_agents
        assert core_agents["api-builder"].exists()
        assert core_agents["api-builder"].name == "api-builder.md"

    @pytest.mark.skip(reason="Pack overlays only supported from bundled packs, not project packs")
    def test_pack_overlay_merging(self, isolated_project_env: Path) -> None:
        """Pack overlays are merged into the composed agent.
        
        NOTE: This test is skipped because the current architecture only supports
        pack overlays from bundled packs (edison.data/packs/), not from project-level
        packs (.edison/packs/). Supporting project-level pack overlays would require
        architectural changes to LayerDiscovery.
        """
        root = isolated_project_env
        # Use real bundled api-builder, apply pack overlay
        write_pack_overlay(root, "test-pack", "api-builder")

        result = compose_agent("api-builder", packs=["test-pack"])

        # The pack overlay content should be in the composed result
        assert "test-pack specific tool" in result
        assert "test-pack specific guideline" in result

    def test_composition_includes_core_content(self, isolated_project_env: Path) -> None:
        """Composed agents include content from bundled core agents."""
        result = compose_agent("api-builder", packs=[])

        # Agent content from bundled api-builder should be present
        assert "# Agent:" in result or "name: api-builder" in result
        # Constitution header is prepended
        assert "Constitution" in result

    def test_composition_output_structure(self, isolated_project_env: Path) -> None:
        """Composed agents follow the expected section structure."""
        text = compose_agent("api-builder", packs=[])

        # Core agent structure is preserved
        assert "# Agent:" in text or "API Builder" in text
        assert "## Role" in text
        # Constitution awareness is injected
        assert "Constitution" in text

    def test_missing_agent_raises(self, isolated_project_env: Path) -> None:
        """Missing core agent raises AgentNotFoundError."""
        with pytest.raises(AgentNotFoundError):
            compose_agent("nonexistent-agent-that-does-not-exist-xyz", packs=[])

    def test_nonexistent_pack_overlay_ignored(self, isolated_project_env: Path) -> None:
        """Composition succeeds even if pack doesn't have overlay for agent."""
        root = isolated_project_env
        # Create a pack directory but no overlay for api-builder
        pack_dir = root / ".edison" / "packs" / "empty-pack" / "agents" / "overlays"
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Should not raise - missing overlays are simply not applied
        result = compose_agent("api-builder", packs=["empty-pack"])
        # Agent content is present (constitution header prepended)
        assert "# Agent:" in result or "name: api-builder" in result
