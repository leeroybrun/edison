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
    def test_registry_loading_from_bundled_core(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Core registry is ALWAYS loaded from bundled edison.data package.
        
        Architecture: Core rules come from bundled data, NOT .edison/rules/.
        Project rules at .edison/rules/ are discovered via discover_project().
        """
        root = isolated_project_env
        
        registry = RulesRegistry(project_root=root)
        core = registry.load_core_registry()

        # Core is always from bundled data
        assert core.get("version") is not None
        assert isinstance(core.get("rules"), list)
        # Bundled core has rules defined
        assert len(core.get("rules", [])) > 0
        
    def test_project_registry_discovered_at_project_root(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Project rules at .edison/rules/registry.yml are discovered as project overrides."""
        root = isolated_project_env
        project_registry = root / ".edison" / "rules" / "registry.yml"

        write_yaml(
            project_registry,
            {
                "version": "2.0.0",
                "rules": [
                    {
                        "id": "project-validation-first",
                        "title": "Project-specific validation rule",
                        "blocking": True,
                        "guidance": "Inline project validation guidance.",
                    }
                ],
            },
        )

        registry = RulesRegistry(project_root=root)
        project_rules = registry.discover_project()

        assert "project-validation-first" in project_rules
        assert project_rules["project-validation-first"]["title"] == "Project-specific validation rule"

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
        """Referencing a non-existent anchor fails fast when extracting from guideline."""
        root = isolated_project_env
        
        # Create a guideline without the expected anchor
        guideline = root / ".edison" / "guidelines" / "BROKEN.md"
        write_guideline(guideline, "# Broken\nNo anchors here.\n")

        # Use static method to test anchor extraction directly
        with pytest.raises(Exception) as exc:
            RulesRegistry.extract_anchor_content(guideline, "does-not-exist")

        # Should mention the missing anchor
        assert "does-not-exist" in str(exc.value)

    def test_pack_rules_merging(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Project pack registries are merged with bundled core rules by ID.
        
        Architecture:
        - Core rules: bundled edison.data/rules/registry.yml
        - Project packs: .edison/packs/<pack>/rules/registry.yml
        """
        root = isolated_project_env

        # Create a project-level pack with its own rules
        react_registry = root / ".edison" / "packs" / "react" / "rules" / "registry.yml"
        write_yaml(
            react_registry,
            {
                "version": "1.0.0",
                "rules": [
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

        # Should have bundled core rules
        assert len(rules) > 0, "Should have bundled core rules"
        
        # Should also have the project pack rule
        assert "react-only" in rules, "Should have react pack rule"

        react_only = rules["react-only"]
        assert react_only["origins"] == ["pack:react"]
        assert "React-only guidance." in react_only["body"]

    def test_circular_include_detection_in_includes(
        self,
        isolated_project_env: Path,
    ) -> None:
        """Circular includes in guidelines are detected when resolving includes."""
        from edison.core.composition.includes import resolve_includes, ComposeError
        
        root = isolated_project_env

        a_path = root / ".edison" / "guidelines" / "A.md"
        b_path = root / ".edison" / "guidelines" / "B.md"

        write_guideline(
            a_path,
            "\n".join(
                [
                    "# A",
                    "Content in A",
                    "{{include:B.md}}",
                ]
            ),
        )
        write_guideline(
            b_path,
            "\n".join(
                [
                    "# B",
                    "Content in B",
                    "{{include:A.md}}",
                ]
            ),
        )

        # Test circular include detection via resolve_includes
        with pytest.raises(ComposeError) as exc:
            resolve_includes(a_path.read_text(), a_path)

        # Should detect circular include or max depth exceeded
        error_msg = str(exc.value).lower()
        assert (
            "include depth" in error_msg
            or "circular" in error_msg
            or "already visited" in error_msg
        ), f"Expected error about circular include or max depth, got: {exc.value}"
