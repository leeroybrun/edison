from __future__ import annotations

from pathlib import Path
import sys
import os
import subprocess

import pytest
from edison.core.utils.subprocess import run_with_timeout


# Ensure Edison core lib is importable


class TestGuidelineCompositionE2E:
    def test_full_pipeline_multi_pack_layers(self, isolated_project_env: Path) -> None:
        """
        End-to-end guideline composition with core + multi-pack + project layers,
        including include resolution chains and shingling-based deduplication.
        """
        from edison.core.composition.guidelines import GuidelineRegistry, compose_guideline 
        root = isolated_project_env

        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        project_dir = root / ".agents" / "guidelines"

        # Core guideline with include chain
        partials = core_dir / "partials"
        partials.mkdir(parents=True, exist_ok=True)

        (partials / "level2.md").write_text("Level 2 details.\n", encoding="utf-8")
        (partials / "level1.md").write_text(
            "Level 1 intro.\n\n{{include:level2.md}}\n\nLevel 1 outro.\n", encoding="utf-8"
        )

        repeated = (
            "common alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu paragraph."
        )

        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "pipeline.md").write_text(
            "# Pipeline Core\n\nCore intro.\n\n{{include:partials/level1.md}}\n\n"
            f"{repeated}\n\nCore tail.\n",
            encoding="utf-8",
        )

        # Two packs extending the guideline
        pack_a_dir = packs_dir / "packA" / "guidelines"
        pack_b_dir = packs_dir / "packB" / "guidelines"
        pack_a_dir.mkdir(parents=True, exist_ok=True)
        pack_b_dir.mkdir(parents=True, exist_ok=True)

        (pack_a_dir / "pipeline.md").write_text(
            "# Pipeline Pack A\n\nPack A intro.\n\n"
            f"{repeated}\n\nPack A specific.\n",
            encoding="utf-8",
        )
        (pack_b_dir / "pipeline.md").write_text(
            "# Pipeline Pack B\n\nPack B intro.\n\n"
            f"{repeated}\n\nPack B specific.\n",
            encoding="utf-8",
        )

        # Project override
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "pipeline.md").write_text(
            "# Pipeline Project\n\nProject intro.\n\n"
            f"{repeated}\n\nProject specific.\n",
            encoding="utf-8",
        )

        registry = GuidelineRegistry()
        names = sorted(registry.all_names(packs=["packA", "packB"], include_project=True))
        assert "pipeline" in names

        text = compose_guideline("pipeline", packs=["packA", "packB"], project_overrides=True)

        # Include chain resolved
        assert "Level 1 intro." in text
        assert "Level 2 details." in text
        assert "Level 1 outro." in text

        # All layers contribute unique content
        assert "Core intro." in text
        assert "Core tail." in text
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
        Circular include chains in guidelines should raise a ComposeError with a helpful message.
        """
        from edison.core.composition.guidelines import compose_guideline 
        from edison.core.composition import ComposeError 
        root = isolated_project_env
        core_dir = root / ".edison" / "core" / "guidelines"
        core_dir.mkdir(parents=True, exist_ok=True)

        (core_dir / "a.md").write_text("# A\n\n{{include:b.md}}\n", encoding="utf-8")
        (core_dir / "b.md").write_text("# B\n\n{{include:a.md}}\n", encoding="utf-8")

        with pytest.raises(ComposeError) as exc:
            compose_guideline("a", packs=[], project_overrides=False)

        msg = str(exc.value)
        assert "Circular include detected" in msg
        assert "a.md" in msg or "b.md" in msg

    def test_cli_composes_guidelines_to_generated_dir(self, isolated_project_env: Path) -> None:
        """
        CLI integration: `compose --guideline` should write composed guidelines
        into .agents/_generated/guidelines/ using the isolated project root.
        """
        root = isolated_project_env

        # Minimum Edison layout under isolated project root
        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        agents_dir = root / ".agents"

        core_dir.mkdir(parents=True, exist_ok=True)
        pack_guides = packs_dir / "packA" / "guidelines"
        pack_guides.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Minimal validator templates required for `compose --all`
        validators_global = root / ".edison" / "core" / "validators" / "global"
        validators_global.mkdir(parents=True, exist_ok=True)
        for role in ("codex", "claude", "gemini"):
            (validators_global / f"{role}.md").write_text(
                f"# {role.title()} Core\n\nBase validator template.\n",
                encoding="utf-8",
            )

        # Core + pack guideline for CLI
        (core_dir / "cli.md").write_text("# CLI Core\n\nCore CLI paragraph.\n", encoding="utf-8")
        (pack_guides / "cli.md").write_text(
            "# CLI Pack\n\nPack CLI paragraph.\n", encoding="utf-8"
        )

        # Minimal config required by ConfigManager in the compose script
        defaults = root / ".edison" / "core" / "defaults.yaml"
        defaults.parent.mkdir(parents=True, exist_ok=True)
        defaults.write_text("packs:\n  active:\n    - packA\n", encoding="utf-8")

        # Write config in modular location
        config_dir = agents_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        project_cfg = config_dir / "packs.yml"
        project_cfg.write_text("packs:\n  active:\n    - packA\n", encoding="utf-8")

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

        out_file = root / ".agents" / "_generated" / "guidelines" / "cli.md"
        assert out_file.exists(), "Expected composed guideline output from CLI"
        content = out_file.read_text(encoding="utf-8")
        assert "Core CLI paragraph." in content
        assert "Pack CLI paragraph." in content

    def test_compose_all_includes_guidelines(self, isolated_project_env: Path) -> None:
        """
        Phase 3A: Composition engine should be able to compose guidelines
        into .agents/_generated/guidelines/ using the same layered pipeline
        used by the CLI's --all mode.
        """
        from edison.core.composition import CompositionEngine 
        root = isolated_project_env

        core_dir = root / ".edison" / "core" / "guidelines"
        packs_dir = root / ".edison" / "packs"
        agents_dir = root / ".agents"

        core_dir.mkdir(parents=True, exist_ok=True)
        pack_guides = packs_dir / "packA" / "guidelines"
        pack_guides.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        (core_dir / "all-md.md").write_text("# Core All\n\nCore ALL paragraph.\n", encoding="utf-8")
        (pack_guides / "all-md.md").write_text(
            "# Pack All\n\nPack ALL paragraph.\n", encoding="utf-8"
        )

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": ["packA"]},
        }

        engine = CompositionEngine(config, repo_root=root)
        results = engine.compose_guidelines(packs_override=["packA"])

        out_file = root / ".agents" / "_generated" / "guidelines" / "all-md.md"
        assert out_file.exists(), "Expected guidelines to be composed via CompositionEngine"
        content = out_file.read_text(encoding="utf-8")
        assert "Core ALL paragraph." in content
        assert "Pack ALL paragraph." in content
        assert "all-md" in results