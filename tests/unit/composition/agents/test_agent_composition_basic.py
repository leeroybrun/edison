"""Tests for basic agent composition functionality.

NO MOCKS - real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition import (
    AgentRegistry,
    AgentNotFoundError,
    compose_agent,
)
from .test_agent_composition_helpers import write_core_agent, write_pack_overlay


class TestAgentCompositionBasic:
    """Tests for basic agent composition operations."""

    def test_agent_discovery_from_core(self, isolated_project_env: Path) -> None:
        """AgentRegistry discovers core agents from .edison/core/agents."""
        root = isolated_project_env
        write_core_agent(root, "api-builder")

        registry = AgentRegistry()
        core_agents = registry.discover_core_agents()

        assert "api-builder" in core_agents
        assert core_agents["api-builder"].name == "api-builder"
        assert core_agents["api-builder"].core_path.exists()

    def test_pack_overlay_merging(self, isolated_project_env: Path) -> None:
        """Pack overlays are merged into the composed agent."""
        root = isolated_project_env
        write_core_agent(root, "api-builder")
        write_pack_overlay(root, "react", "api-builder")

        result = compose_agent("api-builder", packs=["react"])

        # Tools and guidelines from the pack overlay should appear
        assert "react specific tool" in result
        assert "react specific guideline" in result

    def test_template_variable_substitution(self, isolated_project_env: Path) -> None:
        """Unified section placeholders are correctly substituted."""
        root = isolated_project_env
        write_core_agent(root, "api-builder")
        # Two packs to verify multi-pack substitution
        write_pack_overlay(root, "react", "api-builder")
        write_pack_overlay(root, "fastify", "api-builder")

        result = compose_agent("api-builder", packs=["react", "fastify"])

        # Agent name in header
        assert "# Agent: api-builder" in result
        # Pack overlay content is included
        assert "react specific tool" in result
        assert "fastify specific tool" in result
        # No unresolved unified placeholders remain
        for placeholder in (
            "{{SECTION:Tools}}",
            "{{SECTION:Guidelines}}",
            "{{EXTENSIBLE_SECTIONS}}",
            "{{APPEND_SECTIONS}}",
        ):
            assert placeholder not in result

    def test_composition_output_structure(self, isolated_project_env: Path) -> None:
        """Composed agents follow the expected section structure."""
        root = isolated_project_env
        write_core_agent(root, "feature-implementer")

        text = compose_agent("feature-implementer", packs=[])

        assert "# Agent:" in text
        assert "## Role" in text
        assert "## Tools" in text
        assert "## Guidelines" in text
        assert "## Workflows" in text

    def test_missing_agent_raises(self, isolated_project_env: Path) -> None:
        """Missing core agent raises AgentNotFoundError."""
        with pytest.raises(AgentNotFoundError):
            compose_agent("nonexistent-agent", packs=[])

    def test_nonexistent_pack_overlay_ignored(self, isolated_project_env: Path) -> None:
        """Composition succeeds even if pack doesn't have overlay for agent."""
        root = isolated_project_env
        write_core_agent(root, "api-builder")
        # Create a pack directory but no overlay for this agent
        pack_dir = root / ".edison" / "packs" / "empty-pack" / "agents" / "overlays"
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Should not raise - missing overlays are simply not applied
        result = compose_agent("api-builder", packs=["empty-pack"])
        assert "# Agent: api-builder" in result
