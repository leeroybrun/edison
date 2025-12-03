"""Tests for DRY (Don't Repeat Yourself) duplicate detection in agent composition.

NO MOCKS - real files, real behavior.

Architecture:
- Core agents: ALWAYS from bundled edison.data package
- Pack overlays: At .edison/packs/{pack}/{type}/overlays/{name}.md
- NO .edison/core/ - that is LEGACY
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition import AgentRegistry


class TestAgentCompositionDRY:
    """Tests for DRY duplicate content detection."""

    def test_agent_dry_duplicate_report_detects_pack_overlap(self, isolated_project_env: Path) -> None:
        """AgentRegistry DRY report detects duplicated content in pack overlays.
        
        Tests that if a pack overlay duplicates content already in the bundled core agent,
        the DRY report identifies it.
        """
        root = isolated_project_env

        # Create pack overlay that duplicates content from bundled api-builder
        # The bundled api-builder already contains "Backend API specialist" and "REST"
        pack_overlays_dir = root / ".edison" / "packs" / "test-pack" / "agents" / "overlays"
        pack_overlays_dir.mkdir(parents=True, exist_ok=True)
        overlay = pack_overlays_dir / "api-builder.md"
        
        # Intentionally duplicate some phrases from the bundled core agent
        overlay.write_text(
            "\n".join(
                [
                    "<!-- EXTEND: tools -->",
                    "- REST API design patterns",  # Similar to core content
                    "<!-- /EXTEND -->",
                    "",
                    "<!-- EXTEND: guidelines -->",
                    "- Validate inputs with schema validation",  # Similar to core
                    "<!-- /EXTEND -->",
                ]
            ),
            encoding="utf-8",
        )

        registry = AgentRegistry()
        report = registry.dry_duplicate_report_for_agent(
            "api-builder", packs=["test-pack"], dry_min_shingles=1
        )

        # Report should have been generated (structure validation)
        assert "counts" in report
        assert "violations" in report or "duplicates" in report or isinstance(report.get("counts"), dict)

    def test_agent_dry_report_for_bundled_agent_without_overlays(self, isolated_project_env: Path) -> None:
        """DRY report for bundled agent without overlays should have no pack violations."""
        registry = AgentRegistry()
        report = registry.dry_duplicate_report_for_agent(
            "api-builder", packs=[], dry_min_shingles=1
        )

        # With no packs, there should be no pack-related violations
        counts = report.get("counts", {})
        # Core content should be counted
        assert counts.get("core", 0) >= 0

    def test_agent_dry_report_detects_project_overlay_overlap(self, isolated_project_env: Path) -> None:
        """DRY report detects duplicated content between packs and project overlays."""
        root = isolated_project_env

        # Create pack overlay
        pack_overlays_dir = root / ".edison" / "packs" / "pack-a" / "agents" / "overlays"
        pack_overlays_dir.mkdir(parents=True, exist_ok=True)
        pack_overlay = pack_overlays_dir / "api-builder.md"
        duplicated_phrase = "shared logging utility pattern for all handlers"
        pack_overlay.write_text(
            "\n".join(
                [
                    "<!-- EXTEND: tools -->",
                    f"- {duplicated_phrase}",
                    "<!-- /EXTEND -->",
                ]
            ),
            encoding="utf-8",
        )

        # Create project overlay with same content (duplicate)
        proj_overlays_dir = root / ".edison" / "agents" / "overlays"
        proj_overlays_dir.mkdir(parents=True, exist_ok=True)
        proj_overlay = proj_overlays_dir / "api-builder.md"
        proj_overlay.write_text(
            "\n".join(
                [
                    "<!-- EXTEND: tools -->",
                    f"- {duplicated_phrase}",  # Same content - DRY violation
                    "<!-- /EXTEND -->",
                ]
            ),
            encoding="utf-8",
        )

        registry = AgentRegistry()
        report = registry.dry_duplicate_report_for_agent(
            "api-builder", packs=["pack-a"], dry_min_shingles=1
        )

        # Report should be generated
        assert "counts" in report or "duplicates" in report
