from __future__ import annotations

from pathlib import Path
import sys

import pytest

_cur = Path(__file__).resolve()
CORE_ROOT = None
for parent in _cur.parents:
    if (parent / "lib" / "composition" / "__init__.py").exists():
        CORE_ROOT = parent
        break

assert CORE_ROOT is not None, "cannot locate Edison core lib root"

if str(CORE_ROOT) not in sys.path:

from edison.core.agents import (  # type: ignore  # noqa: E402
    AgentRegistry,
    AgentNotFoundError,
    AgentTemplateError,
    compose_agent,
)


class TestAgentCompositionUnit:
    def _write_core_agent(self, root: Path, name: str) -> Path:
        """Create a minimal core agent template."""
        core_agents_dir = root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)
        path = core_agents_dir / f"{name}-core.md"
        content = "\n".join(
            [
                "# Agent: {{AGENT_NAME}}",
                "",
                "## Role",
                "Core role for {{AGENT_NAME}} (packs: {{PACK_NAME}}).",
                "",
                "## Tools",
                "{{TOOLS}}",
                "",
                "## Guidelines",
                "{{GUIDELINES}}",
                "",
                "## Workflows",
                "- Core workflow step",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path

    def _write_pack_overlay(self, root: Path, pack: str, agent: str) -> Path:
        """Create a minimal pack overlay with Tools/Guidelines sections."""
        pack_agents_dir = root / ".edison" / "packs" / pack / "agents"
        pack_agents_dir.mkdir(parents=True, exist_ok=True)
        path = pack_agents_dir / f"{agent}.md"
        content = "\n".join(
            [
                f"# {agent} overlay for {pack}",
                "",
                "## Tools",
                f"- {pack} specific tool",
                "",
                "## Guidelines",
                f"- {pack} specific guideline",
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
        """Template variables like AGENT_NAME and PACK_NAME are substituted."""
        root = isolated_project_env
        self._write_core_agent(root, "api-builder")
        # Two packs to verify multi-pack substitution
        self._write_pack_overlay(root, "react", "api-builder")
        self._write_pack_overlay(root, "fastify", "api-builder")

        result = compose_agent("api-builder", packs=["react", "fastify"])

        # Agent name substituted
        assert "# Agent: api-builder" in result
        # Pack names substituted (comma-separated list)
        assert "react, fastify" in result or "fastify, react" in result
        # No unresolved known placeholders remain
        for placeholder in (
            "{{AGENT_NAME}}",
            "{{PACK_NAME}}",
            "{{TOOLS}}",
            "{{PACK_TOOLS}}",
            "{{GUIDELINES}}",
            "{{PACK_GUIDELINES}}",
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

    def test_invalid_template_raises(self, isolated_project_env: Path) -> None:
        """Invalid core template (missing Agent header) raises AgentTemplateError."""
        root = isolated_project_env
        core_agents_dir = root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)
        bad_core = core_agents_dir / "broken-core.md"
        bad_core.write_text("## Not an agent template", encoding="utf-8")

        with pytest.raises(AgentTemplateError):
            compose_agent("broken", packs=[])

    def test_agent_dry_duplicate_report_detects_overlap(self, isolated_project_env: Path) -> None:
        """AgentRegistry DRY report detects duplicated content between core and pack overlays."""
        root = isolated_project_env
        core_agents_dir = root / ".edison" / "core" / "agents"
        core_agents_dir.mkdir(parents=True, exist_ok=True)

        duplicated = "shared phrase one two three four five six seven eight nine ten eleven twelve"
        core = core_agents_dir / "dup-agent-core.md"
        core.write_text(
            "\n".join(
                [
                    "# Agent: {{AGENT_NAME}}",
                    "",
                    "## Role",
                    "Base role.",
                    "",
                    "## Tools",
                    f"- {duplicated}",
                    "",
                    "## Guidelines",
                    f"- {duplicated}",
                    "",
                    "## Workflows",
                    "- Core workflow step",
                ]
            ),
            encoding="utf-8",
        )

        pack_agents_dir = root / ".edison" / "packs" / "react" / "agents"
        pack_agents_dir.mkdir(parents=True, exist_ok=True)
        overlay = pack_agents_dir / "dup-agent.md"
        overlay.write_text(
            "\n".join(
                [
                    "# dup-agent overlay for react",
                    "",
                    "## Tools",
                    f"- {duplicated}",
                    "",
                    "## Guidelines",
                    "- extra guideline",
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
