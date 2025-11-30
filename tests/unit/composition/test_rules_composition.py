from __future__ import annotations
from helpers.io_utils import write_yaml, write_guideline

from pathlib import Path
import sys

import pytest

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from edison.core.rules import (  # type: ignore  # noqa: E402
    RulesRegistry,
    compose_rules,
)

class TestRulesRegistryAndComposition:
    def test_registry_loading_from_yaml_uses_project_root(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Core registry is loaded from .edison/rules/registry.yml under project root."""
        root = isolated_project_env
        core_registry = root / ".edison" / "rules" / "registry.yml"

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
                        "guidance": "Inline validation guidance.",
                    }
                ],
            },
        )

        guideline = root / ".edison" / "guidelines" / "VALIDATION.md"
        write_guideline(
            guideline,
            "\n".join(
                [
                    "# Validation Guide",
                    "",
                    "<!-- ANCHOR: validation-first -->",
                    "Core validation rule content.",
                    "<!-- END ANCHOR: validation-first -->",
                ]
            ),
        )

        registry = RulesRegistry()
        core = registry.load_core_registry()

        assert core["version"] == "2.0.0"
        assert isinstance(core.get("rules"), list)
        assert core["rules"][0]["id"] == "validation-first"

    def test_anchor_extraction_from_guidelines(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Anchors are extracted between ANCHOR and END ANCHOR markers."""
        root = isolated_project_env
        guideline = root / ".edison" / "guidelines" / "TEST.md"

        write_guideline(
            guideline,
            "\n".join(
                [
                    "# Test Guidelines",
                    "Intro line.",
                    "<!-- ANCHOR: first -->",
                    "First line A.",
                    "First line B.",
                    "<!-- END ANCHOR: first -->",
                    "Outside any anchor.",
                    "<!-- ANCHOR: second -->",
                    "Second anchor content.",
                    # Intentionally omit END marker to exercise implicit termination.
                ]
            ),
        )

        text_first = RulesRegistry.extract_anchor_content(guideline, "first")
        text_second = RulesRegistry.extract_anchor_content(guideline, "second")

        assert "First line A." in text_first
        assert "First line B." in text_first
        assert "Outside any anchor." not in text_first

        assert "Second anchor content." in text_second
        # second anchor should run until EOF when END marker is missing
        assert "<!--" not in text_second

    def test_missing_anchor_raises_error(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Referencing a non-existent anchor fails fast."""
        root = isolated_project_env
        core_registry = root / ".edison" / "rules" / "registry.yml"

        write_yaml(
            core_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "missing-anchor-rule",
                        "title": "Broken rule",
                        "blocking": False,
                        "source": {
                            "file": "guidelines/BROKEN.md",
                            "anchor": "does-not-exist",
                        },
                    }
                ],
            },
        )

        guideline = root / ".edison" / "guidelines" / "BROKEN.md"
        write_guideline(guideline, "# Broken\nNo anchors here.\n")

        with pytest.raises(Exception) as exc:
            compose_rules(packs=[], project_root=root)

        assert "does-not-exist" in str(exc.value)

    def test_pack_rules_merging(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Pack registries are merged with core rules by ID."""
        root = isolated_project_env

        core_registry = root / ".edison" / "rules" / "registry.yml"
        write_yaml(
            core_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "shared-rule",
                        "title": "Core shared rule",
                        "blocking": True,
                        "source": {
                            "file": "guidelines/CORE.md",
                            "anchor": "shared",
                        },
                        "guidance": "Core guidance.",
                    }
                ],
            },
        )

        core_guideline = root / ".edison" / "guidelines" / "CORE.md"
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
        write_yaml(
            react_registry,
            {
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "shared-rule",
                        "title": "React overlay for shared rule",
                        "blocking": False,
                        "guidance": "React-specific guidance.",
                    },
                    {
                        "id": "react-only",
                        "title": "React-only rule",
                        "blocking": False,
                        "guidance": "React-only guidance.",
                    },
                ],
            },
        )

        result = compose_rules(packs=["react"], project_root=root)
        rules = result["rules"]

        assert "shared-rule" in rules
        assert "react-only" in rules

        shared = rules["shared-rule"]
        assert "core" in shared["origins"]
        assert "pack:react" in shared["origins"]
        assert "Core shared content." in shared["body"]
        assert "React-specific guidance." in shared["body"]

        react_only = rules["react-only"]
        assert react_only["origins"] == ["pack:react"]
        assert "React-only guidance." in react_only["body"]

    def test_anchor_resolution_with_includes_and_circular_detection(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Anchors that include files with circular includes surface an error."""
        root = isolated_project_env

        core_registry = root / ".edison" / "rules" / "registry.yml"
        write_yaml(
            core_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "circular",
                        "title": "Circular include rule",
                        "blocking": False,
                        "source": {
                            "file": "guidelines/A.md",
                            "anchor": "a",
                        },
                    }
                ],
            },
        )

        a_path = root / ".edison" / "guidelines" / "A.md"
        b_path = root / ".edison" / "guidelines" / "B.md"

        write_guideline(
            a_path,
            "\n".join(
                [
                    "# A",
                    "<!-- ANCHOR: a -->",
                    "{{include:B.md}}",
                    "<!-- END ANCHOR: a -->",
                ]
            ),
        )
        write_guideline(
            b_path,
            "\n".join(
                [
                    "# B",
                    "<!-- ANCHOR: b -->",
                    "{{include:A.md}}",
                    "<!-- END ANCHOR: b -->",
                ]
            ),
        )

        with pytest.raises(Exception) as exc:
            compose_rules(packs=[], project_root=root)

        # Should detect circular include or max depth exceeded
        error_msg = str(exc.value).lower()
        assert (
            "include depth" in error_msg
            or "circular" in error_msg
        ), f"Expected error about circular include or max depth, got: {exc.value}"
