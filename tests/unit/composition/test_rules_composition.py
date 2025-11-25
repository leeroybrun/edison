from __future__ import annotations

from pathlib import Path
import sys

import pytest


# Ensure Edison core lib is importable (mirror existing tests)
_cur = Path(__file__).resolve()
CORE_ROOT = None
for parent in _cur.parents:
    if (parent / "lib" / "composition" / "__init__.py").exists():
        CORE_ROOT = parent
        break

assert CORE_ROOT is not None, "cannot locate Edison core lib root"

if str(CORE_ROOT) not in sys.path:

from edison.core.rules import (  # type: ignore  # noqa: E402
    RulesRegistry,
    compose_rules,
)


def _write_yaml(path: Path, payload: dict) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_guideline(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestRulesRegistryAndComposition:
    def test_registry_loading_from_yaml_uses_project_root(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Core registry is loaded from .edison/core/rules/registry.yml under project root."""
        root = isolated_project_env
        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"

        _write_yaml(
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

        guideline = root / ".edison" / "core" / "guidelines" / "VALIDATION.md"
        _write_guideline(
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
        guideline = root / ".edison" / "core" / "guidelines" / "TEST.md"

        _write_guideline(
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
        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"

        _write_yaml(
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

        guideline = root / ".edison" / "core" / "guidelines" / "BROKEN.md"
        _write_guideline(guideline, "# Broken\nNo anchors here.\n")

        with pytest.raises(Exception) as exc:
            compose_rules(packs=[])

        assert "does-not-exist" in str(exc.value)

    def test_pack_rules_merging(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Pack registries are merged with core rules by ID."""
        root = isolated_project_env

        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"
        _write_yaml(
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

        core_guideline = root / ".edison" / "core" / "guidelines" / "CORE.md"
        _write_guideline(
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
        _write_yaml(
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

        result = compose_rules(packs=["react"])
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

        core_registry = root / ".edison" / "core" / "rules" / "registry.yml"
        _write_yaml(
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

        a_path = root / ".edison" / "core" / "guidelines" / "A.md"
        b_path = root / ".edison" / "core" / "guidelines" / "B.md"

        _write_guideline(
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
        _write_guideline(
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
            compose_rules(packs=[])

        # Under the hood this is a composition-depth failure; assert we surface something readable.
        assert "Include depth" in str(exc.value) or "circular" in str(exc.value).lower()
