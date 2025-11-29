"""Tests for constitution injection in agent composition.

NO MOCKS - real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import compose_agent
from .test_agent_composition_helpers import write_core_agent


class TestAgentCompositionConstitution:
    """Tests for constitution reference injection."""

    def test_constitution_reference_injected_at_top(self, isolated_project_env: Path) -> None:
        """Composed agent includes constitution reference at the very top."""
        root = isolated_project_env
        write_core_agent(root, "feature-implementer")

        result = compose_agent("feature-implementer", packs=[])

        # Constitution reference should be at the top, before the agent header
        lines = result.strip().split("\n")

        # Find the constitution section
        constitution_found = False
        for i, line in enumerate(lines):
            if "## MANDATORY: Read Constitution First" in line:
                constitution_found = True
                # Verify it's near the top (within first 10 lines)
                assert i < 10, "Constitution reference should be at the top of the prompt"
                break

        assert constitution_found, "Constitution reference section not found in composed agent"

    def test_constitution_path_correct(self, isolated_project_env: Path) -> None:
        """Constitution reference points to correct path."""
        root = isolated_project_env
        write_core_agent(root, "api-builder")

        result = compose_agent("api-builder", packs=[])

        # Check for the correct constitution path
        assert "_generated/constitutions/AGENTS.md" in result, \
            "Constitution path not found or incorrect"

    def test_constitution_includes_reread_instructions(self, isolated_project_env: Path) -> None:
        """Constitution reference includes re-read instructions."""
        root = isolated_project_env
        write_core_agent(root, "database-architect")

        result = compose_agent("database-architect", packs=[])

        # Check for re-read instructions
        assert "Re-read the constitution:" in result or "re-read the constitution" in result.lower(), \
            "Re-read instructions not found in constitution reference"
        assert "At the start of every task" in result or "start of every task" in result.lower(), \
            "Re-read timing instruction not found"

    def test_constitution_injection_happens_automatically(self, isolated_project_env: Path) -> None:
        """Constitution injection happens for all agents automatically during composition."""
        root = isolated_project_env

        # Create multiple agents
        agents = ["api-builder", "feature-implementer", "database-architect"]
        for agent in agents:
            write_core_agent(root, agent)

        # Compose each agent and verify constitution injection
        for agent in agents:
            result = compose_agent(agent, packs=[])

            assert "## MANDATORY: Read Constitution First" in result, \
                f"Constitution reference missing for agent: {agent}"
            assert "_generated/constitutions/AGENTS.md" in result, \
                f"Constitution path missing for agent: {agent}"

    def test_constitution_content_structure(self, isolated_project_env: Path) -> None:
        """Constitution reference includes all required content elements."""
        root = isolated_project_env
        write_core_agent(root, "component-builder")

        result = compose_agent("component-builder", packs=[])

        # Verify all required content elements from the spec
        required_phrases = [
            "MANDATORY",
            "Read Constitution First",
            "_generated/constitutions/AGENTS.md",
            "constitution contains:",
            "mandatory workflow",
            "Applicable rules",
            "Output format",
            "mandatory guideline",
        ]

        for phrase in required_phrases:
            assert phrase.lower() in result.lower(), \
                f"Required phrase '{phrase}' not found in constitution reference"

    def test_constitution_separator_present(self, isolated_project_env: Path) -> None:
        """Constitution reference is separated from agent content with proper markdown separator."""
        root = isolated_project_env
        write_core_agent(root, "refactoring-expert")

        result = compose_agent("refactoring-expert", packs=[])

        # Check for the separator (---) after the constitution section
        assert "---" in result, "Markdown separator not found after constitution reference"

        # Verify separator appears between constitution and agent content
        lines = result.split("\n")
        constitution_idx = -1
        separator_idx = -1
        agent_header_idx = -1

        for i, line in enumerate(lines):
            if "MANDATORY: Read Constitution First" in line:
                constitution_idx = i
            elif line.strip() == "---" and constitution_idx > -1 and separator_idx == -1:
                separator_idx = i
            elif line.startswith("# Agent:") and separator_idx > -1:
                agent_header_idx = i
                break

        assert constitution_idx > -1, "Constitution section not found"
        assert separator_idx > constitution_idx, "Separator not found after constitution"
        assert agent_header_idx > separator_idx, "Agent header not found after separator"
