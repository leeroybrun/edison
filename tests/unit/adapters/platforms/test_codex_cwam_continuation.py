"""Tests for Codex prompts CWAM + continuation guidance injection.

Following STRICT TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor

These tests verify that Codex-synced agent prompts include CWAM (Context Window
Anxiety Management) and continuation guidance via a shared include fragment.

Codex is prompt-sync driven - prompts are synced from .edison/_generated/agents
to .codex/prompts. The guidance should be injected via the agent template
composition system, not by the Codex adapter itself.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.adapters.platforms.codex import CodexAdapter


def _setup_generated_agents_with_cwam(tmp_path: Path) -> None:
    """Set up generated agents directory with agents that should have CWAM/continuation."""
    gen_agents = tmp_path / ".edison" / "_generated" / "agents"
    gen_agents.mkdir(parents=True, exist_ok=True)

    # Agent template should include CWAM/continuation section via shared include
    agent_content = """---
name: test-agent
description: Test agent for CWAM/continuation
model: claude
---
# Agent: Test Agent

## Context & Continuation

Keep working methodically and protect context.
Continue working until the Edison session is complete.
Use the loop driver: `edison session next <session-id>`
"""
    (gen_agents / "test-agent.md").write_text(agent_content, encoding="utf-8")


class TestCodexCwamContinuationGuidance:
    """Tests for CWAM and continuation guidance in Codex-synced prompts."""

    def test_codex_synced_agents_include_cwam_guidance(self, tmp_path: Path) -> None:
        """Codex-synced agents should include CWAM guidance."""
        project_root = tmp_path
        _setup_generated_agents_with_cwam(project_root)

        adapter = CodexAdapter(project_root=project_root)
        result = adapter.sync_all()

        agents = result.get("agents", [])
        assert agents, "Should have synced agents"

        # Check the synced prompt contains CWAM guidance
        synced_path = Path(agents[0])
        content = synced_path.read_text(encoding="utf-8")

        assert "methodically" in content.lower() or "context" in content.lower(), (
            "Codex-synced agent should include CWAM guidance"
        )

    def test_codex_synced_agents_include_continuation_guidance(
        self, tmp_path: Path
    ) -> None:
        """Codex-synced agents should include continuation guidance."""
        project_root = tmp_path
        _setup_generated_agents_with_cwam(project_root)

        adapter = CodexAdapter(project_root=project_root)
        result = adapter.sync_all()

        agents = result.get("agents", [])
        assert agents, "Should have synced agents"

        # Check the synced prompt contains continuation guidance
        synced_path = Path(agents[0])
        content = synced_path.read_text(encoding="utf-8")

        assert (
            "continue" in content.lower() or "session" in content.lower()
        ), "Codex-synced agent should include continuation guidance"


class TestCodexCwamContinuationSharedInclude:
    """Tests for shared include approach in agent templates."""

    def test_agent_templates_use_shared_cwam_continuation_include(self) -> None:
        """Agent templates should use a shared include for CWAM/continuation."""
        # Check that the agent template files use include syntax
        from edison.data import get_data_path

        # Check if agents directory exists in data
        agents_dir = get_data_path("agents")
        assert agents_dir.exists(), "Agents directory not found in data"

        include_marker = "{{include-section:guidelines/includes/CONTINUATION_CWAM.md#embedded}}"
        agent_files = list(agents_dir.glob("*.md"))
        assert agent_files, "No agent templates found"

        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            assert include_marker in content, (
                f"Agent {agent_file.name} should include CWAM/continuation guidance via shared include"
            )

    def test_shared_include_file_exists(self, tmp_path: Path) -> None:
        """A shared CWAM/continuation include file should exist."""
        from edison.data import get_data_path

        includes_dir = get_data_path("guidelines", "includes")
        if not includes_dir.exists():
            pytest.skip("Includes directory not found in data")

        # Check for CWAM/continuation include file
        include_candidates = [
            "CONTINUATION_CWAM.md",
            "CWAM_CONTINUATION.md",
            "SESSION_GUIDANCE.md",
        ]

        found = False
        for candidate in include_candidates:
            if (includes_dir / candidate).exists():
                found = True
                break

        assert found, (
            f"Should have a shared CWAM/continuation include file in {includes_dir}. "
            f"Looked for: {include_candidates}"
        )


class TestCodexCwamContinuationContent:
    """Tests for the content of CWAM/continuation guidance."""

    def test_cwam_guidance_mentions_methodical_work(self, tmp_path: Path) -> None:
        """CWAM guidance should mention working methodically."""
        project_root = tmp_path
        _setup_generated_agents_with_cwam(project_root)

        adapter = CodexAdapter(project_root=project_root)
        result = adapter.sync_all()

        agents = result.get("agents", [])
        if not agents:
            pytest.skip("No agents synced")

        synced_path = Path(agents[0])
        content = synced_path.read_text(encoding="utf-8")

        assert "methodically" in content.lower(), (
            "CWAM guidance should mention working methodically"
        )

    def test_continuation_guidance_mentions_session_next(
        self, tmp_path: Path
    ) -> None:
        """Continuation guidance should mention edison session next."""
        project_root = tmp_path
        _setup_generated_agents_with_cwam(project_root)

        adapter = CodexAdapter(project_root=project_root)
        result = adapter.sync_all()

        agents = result.get("agents", [])
        if not agents:
            pytest.skip("No agents synced")

        synced_path = Path(agents[0])
        content = synced_path.read_text(encoding="utf-8")

        assert "edison session next" in content.lower(), (
            "Continuation guidance should mention edison session next"
        )

    def test_cwam_continuation_section_is_concise(self, tmp_path: Path) -> None:
        """CWAM/continuation section should be concise (minimal tokens)."""
        project_root = tmp_path
        _setup_generated_agents_with_cwam(project_root)

        adapter = CodexAdapter(project_root=project_root)
        result = adapter.sync_all()

        agents = result.get("agents", [])
        if not agents:
            pytest.skip("No agents synced")

        synced_path = Path(agents[0])
        content = synced_path.read_text(encoding="utf-8")

        # Find the Context & Continuation section
        if "## Context & Continuation" in content:
            section_start = content.find("## Context & Continuation")
            # Find next section or end
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1:
                section = content[section_start:]
            else:
                section = content[section_start:next_section]

            lines = [ln for ln in section.strip().split("\n") if ln.strip()]
            # Section should be concise - header + 2-4 guidance lines
            assert len(lines) <= 6, (
                f"Context & Continuation section should be concise, got {len(lines)} lines"
            )
