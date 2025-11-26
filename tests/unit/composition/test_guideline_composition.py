from __future__ import annotations

from pathlib import Path
import sys

import pytest


# Ensure Edison core lib is importable


class TestGuidelineCompositionUnit:
    def test_core_guideline_discovery(self, isolated_project_env: Path) -> None:
        """
        GuidelineRegistry should discover core guidelines under .edison/core/guidelines.
        """
        from edison.core.composition import GuidelineRegistry 
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "architecture.md").write_text("# Core Architecture\n\nCore body.", encoding="utf-8")

        registry = GuidelineRegistry()
        names = registry.all_names(packs=[], include_project=True)

        assert "architecture" in names
        core_path = registry.core_path("architecture")
        assert core_path is not None
        assert core_path.name == "architecture.md"

    def test_pack_guideline_merging(self, isolated_project_env: Path) -> None:
        """
        compose_guideline should merge core + pack guidelines in pack order.
        """
        from edison.core.composition import GuidelineRegistry, compose_guideline 
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"

        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "architecture.md").write_text(
            "# Core Architecture\n\nCore paragraph.\n", encoding="utf-8"
        )

        pack_a_dir = packs_dir / "packA" / "guidelines"
        pack_b_dir = packs_dir / "packB" / "guidelines"
        pack_a_dir.mkdir(parents=True, exist_ok=True)
        pack_b_dir.mkdir(parents=True, exist_ok=True)

        (pack_a_dir / "architecture.md").write_text(
            "# Pack A Architecture\n\nPack A specific paragraph.\n", encoding="utf-8"
        )
        (pack_b_dir / "architecture.md").write_text(
            "# Pack B Architecture\n\nPack B specific paragraph.\n", encoding="utf-8"
        )

        # Sanity: registry resolves pack guideline paths
        registry = GuidelineRegistry()
        pack_paths = registry.pack_paths("architecture", ["packA", "packB"])
        assert [p.parent.parent.name for p in pack_paths] == ["packA", "packB"]

        text = compose_guideline("architecture", packs=["packA", "packB"], project_overrides=False)

        # Core + pack content present
        assert "Core paragraph." in text
        assert "Pack A specific paragraph." in text
        assert "Pack B specific paragraph." in text
        # Pack order respected in final text
        assert text.index("Pack A specific paragraph.") < text.index("Pack B specific paragraph.")

    def test_project_override_application(self, isolated_project_env: Path) -> None:
        """
        Project overrides from .edison/guidelines/*.md should be applied with highest priority.
        """
        from edison.core.composition import compose_guideline
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".edison" / "guidelines"

        core_dir.mkdir(parents=True, exist_ok=True)
        packs_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        (core_dir / "testing.md").write_text("# Core Testing\n\nCore testing guidance.\n", encoding="utf-8")
        (packs_dir / "vitest" / "guidelines").mkdir(parents=True, exist_ok=True)
        (packs_dir / "vitest" / "guidelines" / "testing.md").write_text(
            "# Pack Testing\n\nPack testing guidance.\n", encoding="utf-8"
        )
        (project_dir / "testing.md").write_text(
            "# Project Testing\n\nProject override testing guidance.\n", encoding="utf-8"
        )

        text = compose_guideline("testing", packs=["vitest"], project_overrides=True)

        # All three layers are present
        assert "Core testing guidance." in text
        assert "Pack testing guidance." in text
        assert "Project override testing guidance." in text

        # Project override appears after core and pack sections
        assert text.index("Core testing guidance.") < text.index("Pack testing guidance.")
        assert text.index("Pack testing guidance.") < text.index("Project override testing guidance.")

        # Disabling project overrides should drop project layer
        text_no_override = compose_guideline("testing", packs=["vitest"], project_overrides=False)
        assert "Project override testing guidance." not in text_no_override

    def test_include_resolution(self, isolated_project_env: Path) -> None:
        """
        Includes in guidelines should be resolved via {{include:path}}.
        """
        from edison.core.composition import compose_guideline 
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        core_dir.mkdir(parents=True, exist_ok=True)

        partials_dir = core_dir / "partials"
        partials_dir.mkdir(parents=True, exist_ok=True)

        (partials_dir / "extra.md").write_text("Extra details paragraph.\n", encoding="utf-8")
        (core_dir / "architecture.md").write_text(
            "# Architecture\n\nIntro paragraph.\n\n{{include:partials/extra.md}}\n\nTail paragraph.\n",
            encoding="utf-8",
        )

        text = compose_guideline("architecture", packs=[], project_overrides=False)

        assert "Intro paragraph." in text
        assert "Extra details paragraph." in text
        assert "Tail paragraph." in text

    def test_deduplication_via_shingling(self, isolated_project_env: Path) -> None:
        """
        Duplicate paragraphs across core and packs should be deduplicated using 12-word shingles.
        """
        from edison.core.composition import compose_guideline 
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"

        core_dir.mkdir(parents=True, exist_ok=True)
        (packs_dir / "alpha" / "guidelines").mkdir(parents=True, exist_ok=True)

        repeated = (
            "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu "
            "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu."
        )

        (core_dir / "dedup.md").write_text(f"# Dedup\n\n{repeated}\n", encoding="utf-8")
        (packs_dir / "alpha" / "guidelines" / "dedup.md").write_text(
            f"# Dedup Pack\n\n{repeated}\n\nPack-specific tail.\n", encoding="utf-8"
        )

        text = compose_guideline("dedup", packs=["alpha"], project_overrides=False)

        # The long repeated paragraph should only appear once, but the pack-specific tail should remain.
        assert text.count("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu") == 2
        assert "Pack-specific tail." in text

    def test_layer_priority_enforced(self, isolated_project_env: Path) -> None:
        """
        When duplication exists across layers, project overrides win over packs, and packs win over core.
        """
        from edison.core.composition import compose_guideline
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".edison" / "guidelines"

        core_dir.mkdir(parents=True, exist_ok=True)
        (packs_dir / "alpha" / "guidelines").mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        shared = (
            "shared alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu content paragraph."
        )

        (core_dir / "priority.md").write_text(f"# Priority\n\n{shared}\n\nCORE ONLY.\n", encoding="utf-8")
        (packs_dir / "alpha" / "guidelines" / "priority.md").write_text(
            f"# Priority Pack\n\n{shared}\n\nPACK ONLY.\n", encoding="utf-8"
        )
        (project_dir / "priority.md").write_text(
            f"# Priority Project\n\n{shared}\n\nPROJECT ONLY.\n", encoding="utf-8"
        )

        text = compose_guideline("priority", packs=["alpha"], project_overrides=True)

        # Shared paragraph should appear only once, and PROJECT layer text must be present.
        assert text.count("shared alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu") == 1
        assert "CORE ONLY." in text
        assert "PACK ONLY." in text
        assert "PROJECT ONLY." in text

    def test_guideline_duplicate_report_flags_core_pack_and_project(self, isolated_project_env: Path) -> None:
        """
        Phase 3A: Guideline composition should surface duplicate detection
        across core, packs, and project overlays via duplicate_report.
        """
        from edison.core.composition import GuidelineRegistry
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".edison" / "guidelines"

        core_dir.mkdir(parents=True, exist_ok=True)
        (packs_dir / "alpha" / "guidelines").mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        repeated = (
            "delta alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu paragraph."
        )

        (core_dir / "dup-report.md").write_text(f"# Dup\n\n{repeated}\n", encoding="utf-8")
        (packs_dir / "alpha" / "guidelines" / "dup-report.md").write_text(
            f"# Dup Pack\n\n{repeated}\n", encoding="utf-8"
        )
        (project_dir / "dup-report.md").write_text(
            f"# Dup Project\n\n{repeated}\n", encoding="utf-8"
        )

        registry = GuidelineRegistry()
        result = registry.compose(
            "dup-report",
            packs=["alpha"],
            project_overrides=True,
            dry_min_shingles=1,
        )

        report = result.duplicate_report
        assert report["engineVersion"] != ""
        assert report["counts"]["core"] > 0
        assert report["counts"]["packs"] > 0
        assert report["counts"]["overlay"] > 0
        # At least one violation between core/packs or core/overlay must be recorded.
        pairs = {tuple(v.get("pair", [])) for v in report.get("violations", [])}
        assert ("core", "packs") in pairs or ("core", "overlay") in pairs

    def test_pack_guideline_discovery_supports_namespaced_files(self, isolated_project_env: Path) -> None:
        """
        Phase 3A: Pack guideline discovery should support namespaced filenames
        (e.g. prisma-migrations.md, nextjs-routing.md).
        """
        from edison.core.composition import GuidelineRegistry 
        root = isolated_project_env
        packs_dir = root / ".edison" / "packs"
        prisma_guides = packs_dir / "prisma" / "guidelines"
        prisma_guides.mkdir(parents=True, exist_ok=True)

        (prisma_guides / "prisma-migrations.md").write_text(
            "# prisma Migrations\n\nPack-specific guideline.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry()
        names = registry.all_names(packs=["prisma"], include_project=False)

        assert "prisma-migrations" in names

    def test_guideline_registry_compose_guidelines_writes_generated_files(
        self,
        isolated_project_env: Path,
    ) -> None:
        """
        Phase 3A: GuidelineRegistry.compose should assemble core +
        pack + project guidelines into merged content.
        """
        from edison.core.composition import GuidelineRegistry
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".edison" / "guidelines"

        core_dir.mkdir(parents=True, exist_ok=True)
        (packs_dir / "alpha" / "guidelines").mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        (core_dir / "architecture.md").write_text(
            "# Core Architecture\n\nCore text.\n",
            encoding="utf-8",
        )
        (packs_dir / "alpha" / "guidelines" / "architecture.md").write_text(
            "# Pack Architecture\n\nPack text.\n",
            encoding="utf-8",
        )
        (project_dir / "architecture.md").write_text(
            "# Project Architecture\n\nProject text.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry(repo_root=root)
        result = registry.compose("architecture", ["alpha"])

        # Write to output directory
        out_dir = root / ".edison" / "_generated" / "guidelines"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "architecture.md"
        out_file.write_text(result.text, encoding="utf-8")

        assert out_file.exists(), "Expected composed guideline output"
        content = out_file.read_text(encoding="utf-8")
        assert "Core text." in content
        assert "Pack text." in content
        assert "Project text." in content
