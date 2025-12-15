"""Tests for BATCH 4 consolidation: agent/manifest/constitution helpers.

This test file validates the centralized I/O helpers for writing:
- Generated agent files
- Orchestrator manifests
- Orchestrator constitutions

Following TDD: These tests are written FIRST, then the helpers are implemented.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers.io_utils import (
    write_generated_agent,
    write_orchestrator_constitution,
    write_orchestrator_manifest,
)


class TestWriteGeneratedAgent:
    """Tests for write_generated_agent helper."""

    def test_writes_agent_to_default_location(self, tmp_path: Path) -> None:
        """write_generated_agent creates agent file in .edison/_generated/agents/."""
        path = write_generated_agent(tmp_path, "api-builder")

        assert path == tmp_path / ".edison" / "_generated" / "agents" / "api-builder.md"
        assert path.exists()

        content = path.read_text(encoding="utf-8")
        assert "# Agent: api-builder" in content
        assert "## Role" in content
        assert "## Tools" in content
        assert "## Guidelines" in content
        assert "## Workflows" in content

    def test_writes_agent_with_custom_role_text(self, tmp_path: Path) -> None:
        """write_generated_agent accepts custom role text."""
        path = write_generated_agent(tmp_path, "feature-impl", role_text="Full-stack orchestrator.")

        content = path.read_text(encoding="utf-8")
        assert "Full-stack orchestrator." in content

    def test_writes_agent_with_default_role_text(self, tmp_path: Path) -> None:
        """write_generated_agent generates default role text from name."""
        path = write_generated_agent(tmp_path, "test-agent")

        content = path.read_text(encoding="utf-8")
        # Default role should mention the agent name
        assert "test-agent" in content.lower()

    def test_writes_agent_to_edison_dir_only(self, tmp_path: Path) -> None:
        """write_generated_agent writes only to .edison (no legacy .agents support)."""
        path = write_generated_agent(tmp_path, "custom-agent")
        assert path == tmp_path / ".edison" / "_generated" / "agents" / "custom-agent.md"
        assert path.exists()


class TestWriteOrchestratorManifest:
    """Tests for write_orchestrator_manifest helper."""

    def test_writes_manifest_with_default_data(self, tmp_path: Path) -> None:
        """write_orchestrator_manifest creates manifest with sensible defaults."""
        path = write_orchestrator_manifest(tmp_path)

        assert path == tmp_path / ".edison" / "_generated" / "orchestrator-manifest.json"
        assert path.exists()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert "version" in data
        assert "generated" in data
        assert "composition" in data
        assert "validators" in data
        assert "agents" in data

    def test_writes_manifest_with_custom_agents(self, tmp_path: Path) -> None:
        """write_orchestrator_manifest accepts custom agent roster."""
        agents = {
            "generic": ["feature-implementer"],
            "specialized": ["api-builder", "component-builder"],
            "project": []
        }
        path = write_orchestrator_manifest(tmp_path, agents=agents)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["agents"] == agents
        # agentsCount should reflect total
        assert data["composition"]["agentsCount"] == 3

    def test_writes_manifest_to_edison_dir_only(self, tmp_path: Path) -> None:
        """write_orchestrator_manifest writes only to .edison (no legacy .agents support)."""
        path = write_orchestrator_manifest(tmp_path)
        assert path == tmp_path / ".edison" / "_generated" / "orchestrator-manifest.json"
        assert path.exists()


class TestWriteOrchestratorConstitution:
    """Tests for write_orchestrator_constitution helper."""

    def test_writes_constitution_with_default_content(self, tmp_path: Path) -> None:
        """write_orchestrator_constitution creates constitution with default content."""
        path = write_orchestrator_constitution(tmp_path)

        assert path == tmp_path / ".edison" / "_generated" / "constitutions" / "ORCHESTRATOR.md"
        assert path.exists()

        content = path.read_text(encoding="utf-8")
        assert "# Orchestrator Constitution" in content or "# Test Orchestrator Constitution" in content

    def test_writes_constitution_with_custom_content(self, tmp_path: Path) -> None:
        """write_orchestrator_constitution accepts custom content."""
        custom = "# Custom Constitution\n\n## Section\nDetails."
        path = write_orchestrator_constitution(tmp_path, content=custom)

        content = path.read_text(encoding="utf-8")
        assert content == custom

    def test_writes_constitution_to_edison_dir_only(self, tmp_path: Path) -> None:
        """write_orchestrator_constitution writes only to .edison (no legacy .agents support)."""
        path = write_orchestrator_constitution(tmp_path)
        assert path == tmp_path / ".edison" / "_generated" / "constitutions" / "ORCHESTRATOR.md"
        assert path.exists()
