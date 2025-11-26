from __future__ import annotations

from pathlib import Path
import sys

import pytest

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from edison.core.composition import (  # type: ignore  # noqa: E402
    AgentRegistry,
    AgentNotFoundError,
    AgentTemplateError,
    compose_agent,
)


class TestAgentCompositionUnit:
    def _write_core_agent(self, root: Path, name: str) -> Path:
        """Create a minimal core agent template with unified placeholders."""
        core_agents_dir = root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)
        path = core_agents_dir / f"{name}.md"
        # Use unified section placeholders
        content = "\n".join(
            [
                f"# Agent: {name}",
                "",
                "## Role",
                f"Core role for {name}.",
                "",
                "## Tools",
                "{{SECTION:Tools}}",
                "",
                "## Guidelines",
                "{{SECTION:Guidelines}}",
                "",
                "{{EXTENSIBLE_SECTIONS}}",
                "",
                "{{APPEND_SECTIONS}}",
                "",
                "## Workflows",
                "- Core workflow step",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path

    def _write_pack_overlay(self, root: Path, pack: str, agent: str) -> Path:
        """Create a minimal pack overlay using unified HTML comment syntax."""
        # Overlays must be in the overlays/ subdirectory (unified convention)
        pack_overlays_dir = root / ".edison" / "packs" / pack / "agents" / "overlays"
        pack_overlays_dir.mkdir(parents=True, exist_ok=True)
        path = pack_overlays_dir / f"{agent}.md"
        # Use unified HTML comment markers for section extensions
        content = "\n".join(
            [
                f"<!-- EXTEND: Tools -->",
                f"- {pack} specific tool",
                f"<!-- /EXTEND -->",
                "",
                f"<!-- EXTEND: Guidelines -->",
                f"- {pack} specific guideline",
                f"<!-- /EXTEND -->",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path

    def test_agent_discovery_from_core(self, isolated_project_env: Path) -> None:
        """AgentRegistry discovers core agents from .edison/core/agents."""
        root = isolated_project_env
        self._write_core_agent(root, "api-builder")

        registry = AgentRegistry()
        core_agents = registry.discover_core_agents()

        assert "api-builder" in core_agents
        assert core_agents["api-builder"].name == "api-builder"
        assert core_agents["api-builder"].core_path.exists()

    def test_pack_overlay_merging(self, isolated_project_env: Path) -> None:
        """Pack overlays are merged into the composed agent."""
        root = isolated_project_env
        self._write_core_agent(root, "api-builder")
        self._write_pack_overlay(root, "react", "api-builder")

        result = compose_agent("api-builder", packs=["react"])

        # Tools and guidelines from the pack overlay should appear
        assert "react specific tool" in result
        assert "react specific guideline" in result

    def test_template_variable_substitution(self, isolated_project_env: Path) -> None:
        """Unified section placeholders are correctly substituted."""
        root = isolated_project_env
        self._write_core_agent(root, "api-builder")
        # Two packs to verify multi-pack substitution
        self._write_pack_overlay(root, "react", "api-builder")
        self._write_pack_overlay(root, "fastify", "api-builder")

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
        self._write_core_agent(root, "feature-implementer")

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
        self._write_core_agent(root, "api-builder")
        # Create a pack directory but no overlay for this agent
        pack_dir = root / ".edison" / "packs" / "empty-pack" / "agents" / "overlays"
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Should not raise - missing overlays are simply not applied
        result = compose_agent("api-builder", packs=["empty-pack"])
        assert "# Agent: api-builder" in result

    def test_agent_dry_duplicate_report_detects_overlap(self, isolated_project_env: Path) -> None:
        """AgentRegistry DRY report detects duplicated content between core and pack overlays."""
        root = isolated_project_env
        core_agents_dir = root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)

        duplicated = "shared phrase one two three four five six seven eight nine ten eleven twelve"
        core = core_agents_dir / "dup-agent.md"
        core.write_text(
            "\n".join(
                [
                    "# Agent: dup-agent",
                    "",
                    "## Role",
                    "Base role.",
                    "",
                    "## Tools",
                    "{{SECTION:Tools}}",
                    f"- {duplicated}",
                    "",
                    "## Guidelines",
                    "{{SECTION:Guidelines}}",
                    f"- {duplicated}",
                    "",
                    "{{EXTENSIBLE_SECTIONS}}",
                    "{{APPEND_SECTIONS}}",
                    "",
                    "## Workflows",
                    "- Core workflow step",
                ]
            ),
            encoding="utf-8",
        )

        # Pack overlays must be in the overlays/ subdirectory
        pack_overlays_dir = root / ".edison" / "packs" / "react" / "agents" / "overlays"
        pack_overlays_dir.mkdir(parents=True, exist_ok=True)
        overlay = pack_overlays_dir / "dup-agent.md"
        overlay.write_text(
            "\n".join(
                [
                    "<!-- EXTEND: Tools -->",
                    f"- {duplicated}",
                    "<!-- /EXTEND -->",
                    "",
                    "<!-- EXTEND: Guidelines -->",
                    "- extra guideline",
                    "<!-- /EXTEND -->",
                ]
            ),
            encoding="utf-8",
        )

        registry = AgentRegistry()
        report = registry.dry_duplicate_report_for_agent(
            "dup-agent", packs=["react"], dry_min_shingles=1
        )

        counts = report.get("counts", {})
        violations = report.get("violations", [])

        assert counts.get("core", 0) > 0
        assert counts.get("packs", 0) > 0
        assert any(v.get("pair") == ["core", "packs"] for v in violations)

    def test_constitution_reference_injected_at_top(self, isolated_project_env: Path) -> None:
        """Composed agent includes constitution reference at the very top."""
        root = isolated_project_env
        self._write_core_agent(root, "feature-implementer")

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
        self._write_core_agent(root, "api-builder")

        result = compose_agent("api-builder", packs=[])

        # Check for the correct constitution path
        assert "_generated/constitutions/AGENTS.md" in result, \
            "Constitution path not found or incorrect"

    def test_constitution_includes_reread_instructions(self, isolated_project_env: Path) -> None:
        """Constitution reference includes re-read instructions."""
        root = isolated_project_env
        self._write_core_agent(root, "database-architect")

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
            self._write_core_agent(root, agent)

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
        self._write_core_agent(root, "component-builder")

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
        self._write_core_agent(root, "refactoring-expert")

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
