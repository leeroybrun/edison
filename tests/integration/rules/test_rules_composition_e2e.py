from __future__ import annotations
from helpers.io_utils import write_yaml, write_guideline

from pathlib import Path
import sys
import os
import json
import subprocess

import pytest

from edison.core.rules import RulesRegistry, compose_rules
from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path

class TestRulesCompositionE2E:
    def test_full_rules_composition_pipeline_in_isolated_env(
        self,
        isolated_project_env: Path,
    ) -> None:
        """
        Compose rules end-to-end in an isolated project environment.

        This exercises registry loading, anchor extraction, and composition.
        """
        root = isolated_project_env

        # Core registry & guideline
        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"
        write_yaml(
            core_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "validation-first",
                        "title": "Always validate before implementing",
                        "blocking": True,
                        "source": {
                            "file": "guidelines/VALIDATION.md",
                            "anchor": "validation-first",
                        },
                        "guidance": "Never skip validation in this project.",
                    }
                ],
            },
        )

        guideline = root / ".edison" / "core" / "guidelines" / "VALIDATION.md"
        write_guideline(
            guideline,
            "\n".join(
                [
                    "# Validation Guide",
                    "",
                    "<!-- ANCHOR: validation-first -->",
                    "Anchored validation content.",
                    "<!-- END ANCHOR: validation-first -->",
                ]
            ),
        )

        registry = RulesRegistry(project_root=root)
        result = registry.compose(packs=[])

        assert result["version"] == "2.0.0"
        rules = result["rules"]
        assert "validation-first" in rules

        rf = rules["validation-first"]
        assert rf["blocking"] is True
        assert "Anchored validation content." in rf["body"]
        assert "Never skip validation in this project." in rf["body"]

    def test_multi_pack_rules_composition(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Multiple packs can contribute overlays to the same rule ID."""
        root = isolated_project_env

        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"
        write_yaml(
            core_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "shared-rule",
                        "title": "Core shared rule",
                        "blocking": False,
                        "source": {
                            "file": "guidelines/CORE.md",
                            "anchor": "shared",
                        },
                        "guidance": "Core guidance.",
                    }
                ],
            },
        )

        core_guideline = root / ".edison" / "core" / "guidelines" / "CORE.md"
        write_guideline(
            core_guideline,
            "\n".join(
                [
                    "# Core",
                    "<!-- ANCHOR: shared -->",
                    "Core shared content.",
                    "<!-- END ANCHOR: shared -->",
                ]
            ),
        )

        react_registry = root / ".edison" / "packs" / "react" / "rules" / "registry.yml"
        next_registry = root / ".edison" / "packs" / "nextjs" / "rules" / "registry.yml"

        write_yaml(
            react_registry,
            {
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "shared-rule",
                        "title": "React overlay",
                        "blocking": True,
                        "guidance": "React-specific overlay guidance.",
                    }
                ],
            },
        )

        write_yaml(
            next_registry,
            {
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "shared-rule",
                        "guidance": "nextjs-specific overlay guidance.",
                    }
                ],
            },
        )

        result = compose_rules(packs=["react", "nextjs"])
        rules = result["rules"]
        assert "shared-rule" in rules

        shared = rules["shared-rule"]
        # Blocking becomes True once any pack marks it blocking
        assert shared["blocking"] is True
        # Origins include core and both packs
        assert "core" in shared["origins"]
        assert "pack:react" in shared["origins"]
        assert "pack:nextjs" in shared["origins"]
        # All guidance segments are present in composed body
        body = shared["body"]
        assert "Core shared content." in body
        assert "React-specific overlay guidance." in body
        assert "nextjs-specific overlay guidance." in body

    def test_core_registry_anchors_are_valid_for_real_repo(
        self,
        isolated_project_env: Path,
    ) -> None:
        """
        Real core registry should have valid anchor references.

        This mirrors rules_verify_anchors.py but uses RulesRegistry helpers.
        """
        # Try to find wilson-leadgen project, else skip
        repo_root = None
        _cur = Path(__file__).resolve()
        for parent in _cur.parents:
            if (parent / ".agents" / "config").exists() and (parent / ".edison").exists():
                repo_root = parent
                break

        if not repo_root:
            pytest.skip("wilson-leadgen project not found - test requires project with .edison directory")

        registry = RulesRegistry(project_root=repo_root)
        core = registry.load_core_registry()

        errors: list[str] = []

        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            source_file, anchor = registry._resolve_source(raw_rule)  # type: ignore[attr-defined]
            if not source_file or not anchor:
                continue
            try:
                RulesRegistry.extract_anchor_content(source_file, anchor)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"{raw_rule.get('id')}: {exc}")

        assert not errors, "Core registry has invalid anchors:\n" + "\n".join(errors)

    def test_rules_compose_cli_writes_composed_rules_file(
        self,
        isolated_project_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        scripts/rules compose should write composed rules JSON into .agents/_generated/rules/.
        """
        root = isolated_project_env

        # Minimal core registry & guideline in isolated project
        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"
        write_yaml(
            core_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "cli-rule",
                        "title": "CLI Rule",
                        "blocking": False,
                        "source": {
                            "file": "guidelines/CLI.md",
                            "anchor": "cli-anchor",
                        },
                        "guidance": "CLI-specific guidance.",
                    }
                ],
            },
        )

        guideline = root / ".edison" / "core" / "guidelines" / "CLI.md"
        write_guideline(
            guideline,
            "\n".join(
                [
                    "# CLI Guidelines",
                    "<!-- ANCHOR: cli-anchor -->",
                    "CLI anchor content.",
                    "<!-- END ANCHOR: cli-anchor -->",
                ]
            ),
        )

        # Try to find edison repository with scripts
        repo_root = None
        _cur = Path(__file__).resolve()
        for parent in _cur.parents:
            potential_script = parent / "scripts" / "rules"
            if potential_script.exists():
                repo_root = parent
                break

        if not repo_root:
            pytest.skip("Edison repository with scripts not found - test requires development environment")

        script_path = repo_root / "scripts" / "rules"

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        proc = run_with_timeout(
            [sys.executable, str(script_path), "compose"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr

        out_path = root / ".agents" / "_generated" / "rules" / "rules.json"
        assert out_path.exists(), "Composed rules file not created by CLI"

        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "cli-rule" in data.get("rules", {})
