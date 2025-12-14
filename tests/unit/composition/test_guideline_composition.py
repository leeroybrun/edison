"""Tests for guideline composition (unified GenericRegistry).

Key invariants:
- Nested guideline paths are preserved as entity keys (e.g. "shared/INDEX").
- include-only guideline fragments under "guidelines/includes/**" are first-class
  composable artifacts and can be extended via EXTEND blocks from overlays.
"""
from __future__ import annotations

from pathlib import Path


class TestGuidelineCompositionUnit:
    """Tests for guideline composition with correct architecture."""

    def test_core_guideline_discovery(self, isolated_project_env: Path) -> None:
        """Core guidelines are discovered with nested keys (incl. includes/**)."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry("guidelines", project_root=isolated_project_env)
        names = registry.all_names(packs=[], include_project=False)

        assert "shared/INDEX" in names
        assert "includes/TDD" in names
        assert len(names) > 0

    def test_core_guideline_path_resolution(self, isolated_project_env: Path) -> None:
        """Core guideline paths come from bundled data, not project overlays."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry("guidelines", project_root=isolated_project_env)
        core_path = registry.core_path("shared/INDEX")
        assert core_path is not None
        assert ".edison/core" not in str(core_path)
        assert "src/edison/data/guidelines" in str(core_path).replace("\\", "/")

    def test_pack_guideline_discovery_from_project_packs(self, isolated_project_env: Path) -> None:
        """Pack guidelines from project packs (.edison/packs/) should be discovered."""
        from edison.core.composition.registries.generic import GenericRegistry

        root = isolated_project_env
        packs_dir = root / ".edison" / "packs"

        # Create a project-level pack guideline
        pack_guides = packs_dir / "my-pack" / "guidelines"
        pack_guides.mkdir(parents=True, exist_ok=True)
        (pack_guides / "my-custom-guide.md").write_text(
            "# My Custom Guide\n\nPack-specific content.\n",
            encoding="utf-8",
        )

        registry = GenericRegistry("guidelines", project_root=root)
        names = registry.all_names(packs=["my-pack"], include_project=False)

        assert "my-custom-guide" in names

    def test_project_override_discovery(self, isolated_project_env: Path) -> None:
        """Project guidelines from .edison/guidelines/ should be discovered."""
        from edison.core.composition.registries.generic import GenericRegistry

        root = isolated_project_env
        project_dir = root / ".edison" / "guidelines"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "project-specific.md").write_text(
            "# Project Specific\n\nProject guideline.\n",
            encoding="utf-8",
        )

        registry = GenericRegistry("guidelines", project_root=root)
        names = registry.all_names(packs=[], include_project=True)

        assert "project-specific" in names

    def test_project_overlay_applies_to_core_guideline(self, isolated_project_env: Path) -> None:
        """Project overlays under .edison/guidelines/overlays/** are applied (highest priority)."""
        from edison.core.composition.registries.generic import GenericRegistry

        root = isolated_project_env
        overlays_dir = root / ".edison" / "guidelines" / "overlays" / "shared"
        overlays_dir.mkdir(parents=True, exist_ok=True)
        (overlays_dir / "VALIDATION.md").write_text(
            "# Project Validation Overlay\n\nProject overlay marker.\n",
            encoding="utf-8",
        )

        registry = GenericRegistry("guidelines", project_root=root)
        text = registry.compose("shared/VALIDATION", packs=[]) or ""
        assert "Project overlay marker." in text

    def test_include_only_files_support_extend_and_include_section(self, isolated_project_env: Path) -> None:
        """EXTEND blocks against include-only files affect include-section consumers."""
        from edison.core.composition.registries.generic import GenericRegistry
        from edison.core.composition.registries.constitutions import ConstitutionRegistry

        root = isolated_project_env

        # Extend the "principles" section in guidelines/includes/TDD.md
        overlays_dir = root / ".edison" / "guidelines" / "overlays" / "includes"
        overlays_dir.mkdir(parents=True, exist_ok=True)
        (overlays_dir / "TDD.md").write_text(
            "<!-- extend: principles -->\nPROJECT_TDD_EXT_MARKER\n<!-- /extend -->\n",
            encoding="utf-8",
        )

        # Sanity: the include-only file itself composes and contains the merged extension.
        guide_reg = GenericRegistry("guidelines", project_root=root)
        include_text = guide_reg.compose("includes/TDD", packs=[]) or ""
        assert "PROJECT_TDD_EXT_MARKER" in include_text

        # And consumers that use include-section see the updated section content.
        const_reg = ConstitutionRegistry(project_root=root)
        agents_text = const_reg.compose("agents", packs=[]) or ""
        assert "PROJECT_TDD_EXT_MARKER" in agents_text
