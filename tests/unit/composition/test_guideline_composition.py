"""Tests for guideline composition.

Architecture:
- Core guidelines: ALWAYS from bundled edison.data/guidelines/
- Pack guidelines: From bundled packs + project packs at .edison/packs/{pack}/guidelines/
- Project overrides: At .edison/guidelines/
- NO .edison/core/ - that is LEGACY
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestGuidelineCompositionUnit:
    """Tests for guideline composition with correct architecture."""

    def test_core_guideline_discovery(self, isolated_project_env: Path) -> None:
        """GuidelineRegistry discovers core guidelines from bundled edison.data."""
        from edison.core.composition import GuidelineRegistry

        registry = GuidelineRegistry()
        names = registry.all_names(packs=[], include_project=False)

        # Bundled core guidelines should be discovered
        assert "TDD" in names or "COMMON" in names  # Real bundled guidelines
        # Verify at least some core guidelines exist
        assert len(names) > 0

    def test_core_guideline_path_resolution(self, isolated_project_env: Path) -> None:
        """Core guideline paths should be from bundled data, not .edison/core/."""
        from edison.core.composition import GuidelineRegistry

        registry = GuidelineRegistry()
        names = registry.all_names(packs=[], include_project=False)

        if names:
            core_path = registry.core_path(names[0])
            assert core_path is not None
            # Path should NOT be in .edison/core/
            assert ".edison/core" not in str(core_path)
            # Path should be in bundled data
            assert "edison" in str(core_path) and "data" in str(core_path)

    def test_pack_guideline_discovery_from_project_packs(self, isolated_project_env: Path) -> None:
        """Pack guidelines from project packs (.edison/packs/) should be discovered."""
        from edison.core.composition import GuidelineRegistry

        root = isolated_project_env
        packs_dir = root / ".edison" / "packs"

        # Create a project-level pack guideline
        pack_guides = packs_dir / "my-pack" / "guidelines"
        pack_guides.mkdir(parents=True, exist_ok=True)
        (pack_guides / "my-custom-guide.md").write_text(
            "# My Custom Guide\n\nPack-specific content.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry()
        names = registry.all_names(packs=["my-pack"], include_project=False)

        assert "my-custom-guide" in names

    def test_project_override_discovery(self, isolated_project_env: Path) -> None:
        """Project overlays from .edison/guidelines/overlays should be discovered."""
        from edison.core.composition import GuidelineRegistry

        root = isolated_project_env
        project_dir = root / ".edison" / "guidelines"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "project-specific.md").write_text(
            "# Project Specific\n\nProject guideline.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry()
        names = registry.all_names(packs=[], include_project=True)

        assert "project-specific" in names

    def test_project_override_application(self, isolated_project_env: Path) -> None:
        """Project guidelines at .edison/guidelines/ are concatenated with highest priority."""
        from edison.core.composition import compose_guideline

        root = isolated_project_env
        project_dir = root / ".edison" / "guidelines"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Use a real bundled guideline name and create project override
        (project_dir / "TDD.md").write_text(
            "# Project TDD\n\nProject TDD override.\n",
            encoding="utf-8",
        )

        text = compose_guideline("TDD", packs=[], project_overrides=True)

        # Project override content should be present
        assert "Project TDD override." in text

    def test_compose_without_project_overrides(self, isolated_project_env: Path) -> None:
        """Disabling project overrides should exclude project layer."""
        from edison.core.composition import compose_guideline

        root = isolated_project_env
        project_dir = root / ".edison" / "guidelines"
        project_dir.mkdir(parents=True, exist_ok=True)

        (project_dir / "TDD.md").write_text(
            "# Project TDD\n\nProject TDD override.\n",
            encoding="utf-8",
        )

        text_no_override = compose_guideline("TDD", packs=[], project_overrides=False)

        # Project layer should be excluded when project_overrides=False
        assert "Project TDD override." not in text_no_override

    def test_pack_guideline_discovery_supports_namespaced_files(self, isolated_project_env: Path) -> None:
        """Pack guideline discovery supports namespaced filenames (e.g. prisma-migrations.md)."""
        from edison.core.composition import GuidelineRegistry

        root = isolated_project_env
        packs_dir = root / ".edison" / "packs"
        prisma_guides = packs_dir / "prisma" / "guidelines"
        prisma_guides.mkdir(parents=True, exist_ok=True)

        (prisma_guides / "prisma-migrations.md").write_text(
            "# Prisma Migrations\n\nPack-specific guideline.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry()
        names = registry.all_names(packs=["prisma"], include_project=False)

        assert "prisma-migrations" in names

    def test_guideline_registry_compose_with_project_pack(self, isolated_project_env: Path) -> None:
        """GuidelineRegistry composes bundled core + project pack + project override."""
        from edison.core.composition import GuidelineRegistry

        root = isolated_project_env
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".edison" / "guidelines" / "overlays"

        # Create project pack guideline
        (packs_dir / "alpha" / "guidelines").mkdir(parents=True, exist_ok=True)
        (packs_dir / "alpha" / "guidelines" / "alpha-guide.md").write_text(
            "# Alpha Guide\n\nPack text.\n",
            encoding="utf-8",
        )

        # Create project override for the same guideline
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "alpha-guide.md").write_text(
            "# Project Alpha Guide\n\nProject text.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry(project_root=root)
        result = registry.compose("alpha-guide", ["alpha"])

        # Both pack and project content should be present
        assert "Pack text." in result.text
        assert "Project text." in result.text

    def test_compose_bundled_guideline(self, isolated_project_env: Path) -> None:
        """Compose a real bundled guideline without modifications."""
        from edison.core.composition import compose_guideline

        # TDD is a real bundled guideline
        text = compose_guideline("TDD", packs=[], project_overrides=False)

        # Should contain actual guideline content
        assert len(text) > 100  # Real content is substantial
        # Should NOT have unresolved markers
        assert "{{" not in text or "{{#" in text  # Allow loop markers

    def test_duplicate_report_with_project_pack(self, isolated_project_env: Path) -> None:
        """Duplicate detection works with project packs."""
        from edison.core.composition import GuidelineRegistry

        root = isolated_project_env
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".edison" / "guidelines" / "overlays"

        # Create duplicate content across pack and project
        repeated = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu paragraph."

        (packs_dir / "alpha" / "guidelines").mkdir(parents=True, exist_ok=True)
        (packs_dir / "alpha" / "guidelines" / "dup-test.md").write_text(
            f"# Dup Pack\n\n{repeated}\n",
            encoding="utf-8",
        )

        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "dup-test.md").write_text(
            f"# Dup Project\n\n{repeated}\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry()
        result = registry.compose(
            "dup-test",
            packs=["alpha"],
            project_overrides=True,
            dry_min_shingles=1,
        )

        report = result.duplicate_report
        assert report["engineVersion"] != ""
        # Should detect duplicates between layers
        assert report["counts"]["packs"] > 0 or report["counts"]["overlay"] > 0
