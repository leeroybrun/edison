"""Tests for DRY (Don't Repeat Yourself) duplicate detection in agent composition.

NO MOCKS - real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import AgentRegistry


class TestAgentCompositionDRY:
    """Tests for DRY duplicate content detection."""

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
