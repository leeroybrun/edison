from __future__ import annotations

from pathlib import Path
import os

import pytest
from edison.core.utils.subprocess import run_with_timeout


class TestGuidelineCompositionE2E:
    def test_full_pipeline_multi_pack_layers(self, isolated_project_env: Path) -> None:
        """
        End-to-end guideline composition with:
        - core guideline (bundled edison.data)
        - project packs (.edison/packs/<pack>/guidelines/overlays/**)
        - project overlays (.edison/guidelines/overlays/**)
        - include resolution via composed entities (guidelines/partials/**)
        - shingling-based deduplication enabled for guidelines
        """
        from edison.core.composition.registries.generic import GenericRegistry
        root = isolated_project_env

        # Minimal pack activation config
        config_dir = root / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "packs.yml").write_text(
            "packs:\n  active:\n    - packA\n    - packB\n",
            encoding="utf-8",
        )

        # Project "partials" used by include chains (composed entities)
        partials = root / ".edison" / "guidelines" / "partials"
        partials.mkdir(parents=True, exist_ok=True)
        (partials / "level2.md").write_text("Level 2 details.\n", encoding="utf-8")
        (partials / "level1.md").write_text(
            "Level 1 intro.\n\n{{include:guidelines/partials/level2.md}}\n\nLevel 1 outro.\n",
            encoding="utf-8",
        )

        # We'll overlay an existing core guideline so packs can extend it.
        target = "shared/PRINCIPLES_REFERENCE"

        repeated = "common alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu paragraph."

        # Two project packs overlaying the same core guideline
        pack_a_over = root / ".edison" / "packs" / "packA" / "guidelines" / "overlays" / "shared"
        pack_b_over = root / ".edison" / "packs" / "packB" / "guidelines" / "overlays" / "shared"
        pack_a_over.mkdir(parents=True, exist_ok=True)
        pack_b_over.mkdir(parents=True, exist_ok=True)

        (pack_a_over / "PRINCIPLES_REFERENCE.md").write_text(
            "# Pack A Overlay\n\n{{include:guidelines/partials/level1.md}}\n\n"
            f"{repeated}\n\nPack A specific.\n",
            encoding="utf-8",
        )
        (pack_b_over / "PRINCIPLES_REFERENCE.md").write_text(
            "# Pack B Overlay\n\n"
            f"{repeated}\n\nPack B specific.\n",
            encoding="utf-8",
        )

        # Project overlay (highest priority)
        project_over = root / ".edison" / "guidelines" / "overlays" / "shared"
        project_over.mkdir(parents=True, exist_ok=True)
        (project_over / "PRINCIPLES_REFERENCE.md").write_text(
            "# Project Overlay\n\n"
            f"{repeated}\n\nProject specific.\n",
            encoding="utf-8",
        )

        registry = GenericRegistry("guidelines", project_root=root)
        names = sorted(registry.all_names(packs=["packA", "packB"], include_project=True))
        assert target in names

        text = registry.compose(target, packs=["packA", "packB"]) or ""

        # Include chain resolved
        assert "Level 1 intro." in text
        assert "Level 2 details." in text
        assert "Level 1 outro." in text

        # All layers contribute unique content
        assert "Pack A specific." in text
        assert "Pack B specific." in text
        assert "Project specific." in text

        # Shared repeated paragraph should only appear once (highest-priority project layer wins).
        assert text.count(
            "common alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
        ) == 1

    def test_include_circular_dependencies_surface_clear_error(
        self, isolated_project_env: Path
    ) -> None:
        """
        Circular include chains in composed-entity includes should surface a clear marker.
        """
        from edison.core.composition.registries.generic import GenericRegistry
        root = isolated_project_env

        # Create circular include chain as project guidelines.
        partials = root / ".edison" / "guidelines" / "partials"
        partials.mkdir(parents=True, exist_ok=True)
        (partials / "a.md").write_text("# A\n\n{{include:guidelines/partials/b.md}}\n", encoding="utf-8")
        (partials / "b.md").write_text("# B\n\n{{include:guidelines/partials/a.md}}\n", encoding="utf-8")

        # Overlay a real core guideline to pull in the chain.
        project_over = root / ".edison" / "guidelines" / "overlays" / "shared"
        project_over.mkdir(parents=True, exist_ok=True)
        (project_over / "PRINCIPLES_REFERENCE.md").write_text(
            "{{include:guidelines/partials/a.md}}\n",
            encoding="utf-8",
        )

        registry = GenericRegistry("guidelines", project_root=root)
        from edison.core.composition.core.errors import CompositionValidationError

        with pytest.raises(CompositionValidationError) as excinfo:
            registry.compose("shared/PRINCIPLES_REFERENCE", packs=[])

        assert "Circular composed-include detected" in str(excinfo.value)

    def test_cli_composes_guidelines_to_generated_dir(self, isolated_project_env: Path) -> None:
        """
        CLI integration: `edison compose all --guidelines` writes to
        .edison/_generated/guidelines/ under the isolated project root.
        """
        root = isolated_project_env

        # Project guideline to be composed
        guides_dir = root / ".edison" / "guidelines"
        guides_dir.mkdir(parents=True, exist_ok=True)
        (guides_dir / "cli.md").write_text("# CLI\n\nCLI paragraph.\n", encoding="utf-8")

        # Invoke the real compose CLI under the isolated project root
        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        proc = run_with_timeout(
            ["uv", "run", "edison", "compose", "all", "--guidelines"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

        out_file = root / ".edison" / "_generated" / "guidelines" / "cli.md"
        assert out_file.exists(), "Expected composed guideline output from CLI"
        content = out_file.read_text(encoding="utf-8")
        assert "CLI paragraph." in content
