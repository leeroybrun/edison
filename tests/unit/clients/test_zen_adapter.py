from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.adapters import ZenAdapter
from tests.helpers.io_utils import write_yaml


class TestZenAdapterUnit:
    def _write_basic_config(self, root: Path) -> None:
        """Write modular config overlays in the new YAML layout."""
        config_dir = root / ".edison" / "config"

        # Explicit pack activation (none for the baseline tests)
        write_yaml(config_dir / "packs.yaml", {"packs": {"active": []}})

        # Zen roles must use mapping form (no legacy lists) to satisfy validator.
        write_yaml(config_dir / "zen.yaml", {
            "zen": {
                "enabled": True,
                "roles": {
                    "codex": {},
                    "claude": {},
                    "gemini": {}
                }
            }
        })

        # Minimal project config for ConfigManager
        project_config_path = root / ".edison" / "config" / "project.yaml"
        if not project_config_path.exists():
            write_yaml(project_config_path, {"project": {"name": "test-project"}})

    def _write_config_with_project_roles(self, root: Path) -> None:
        """Config with active packs and zen.roles mapping for project roles."""
        config_dir = root / ".edison" / "config"

        # Project packs are declared in modular overlay form.
        write_yaml(config_dir / "packs.yaml", {
            "packs": {
                "active": ["fastify", "prisma"]
            }
        })

        # Role mapping now lives under zen.yaml with per-role mappings.
        write_yaml(config_dir / "zen.yaml", {
            "zen": {
                "enabled": True,
                "roles": {
                    "project-api-builder": {
                        "guidelines": ["api-design", "validation", "error-handling"],
                        "rules": ["validation", "implementation"],
                        "packs": ["fastify"]
                    }
                }
            }
        })

        project_config_path = root / ".edison" / "config" / "project.yaml"
        if not project_config_path.exists():
            write_yaml(project_config_path, {"project": {"name": "test-project"}})

    def _write_guidelines(self, root: Path) -> None:
        """Create a small guideline set with role-specific markers."""
        gdir = root / ".edison" / "guidelines"
        gdir.mkdir(parents=True, exist_ok=True)

        (gdir / "QUALITY.md").write_text("QUALITY-GUIDE\n", encoding="utf-8")
        (gdir / "security.md").write_text("SECURITY-GUIDE\n", encoding="utf-8")
        (gdir / "performance.md").write_text("PERFORMANCE-GUIDE\n", encoding="utf-8")
        (gdir / "architecture.md").write_text("ARCHITECTURE-GUIDE\n", encoding="utf-8")

    def _write_guidelines_with_packs_and_overlays(self, root: Path) -> None:
        """Create guidelines across bundled + packs to exercise mapping engine."""
        core_dir = root / ".edison" / "guidelines"
        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "api-design.md").write_text("CORE-API-DESIGN\n", encoding="utf-8")
        (core_dir / "validation.md").write_text("CORE-VALIDATION\n", encoding="utf-8")
        (core_dir / "error-handling.md").write_text("CORE-ERROR-HANDLING\n", encoding="utf-8")
        (core_dir / "other.md").write_text("CORE-OTHER\n", encoding="utf-8")

        fastify_dir = root / ".edison" / "packs" / "fastify" / "guidelines"
        fastify_dir.mkdir(parents=True, exist_ok=True)
        (fastify_dir / "schema-validation.md").write_text(
            "FASTIFY-SCHEMA-VALIDATION\n", encoding="utf-8"
        )
        (fastify_dir / "error-handling.md").write_text(
            "FASTIFY-ERROR-HANDLING\n", encoding="utf-8"
        )

        prisma_dir = root / ".edison" / "packs" / "prisma" / "guidelines"
        prisma_dir.mkdir(parents=True, exist_ok=True)
        (prisma_dir / "schema-design.md").write_text(
            "prisma-SCHEMA-DESIGN\n", encoding="utf-8"
        )

        project_guides = root / ".edison" / "guidelines"
        project_guides.mkdir(parents=True, exist_ok=True)
        (project_guides / "api-design.md").write_text(
            "PROJECT-API-DESIGN-OVERLAY\n", encoding="utf-8"
        )

    def _write_rules_registry(self, root: Path) -> None:
        registry_data = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "RULE.REVIEW.VALIDATION",
                    "title": "Validation rule for reviews",
                    "category": "validation",
                    "blocking": True
                },
                {
                    "id": "RULE.REVIEW.IMPLEMENTATION",
                    "title": "Implementation rule for reviews",
                    "category": "implementation",
                    "blocking": False
                },
                {
                    "id": "RULE.PLANNING.DELEGATION",
                    "title": "Delegation planning rule",
                    "category": "delegation",
                    "blocking": False
                },
                {
                    "id": "RULE.PLANNING.SESSION",
                    "title": "Session planning rule",
                    "category": "session",
                    "blocking": False
                }
            ]
        }
        write_yaml(root / ".edison" / "rules" / "registry.yaml", registry_data)

    def _write_rules_with_packs(self, root: Path) -> None:
        """Create core + pack rule registries for category/pack filtering."""
        core_registry = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "RULE.CORE.VALIDATION",
                    "title": "Core validation rule",
                    "category": "validation",
                    "blocking": False
                },
                {
                    "id": "RULE.CORE.IMPLEMENTATION",
                    "title": "Core implementation rule",
                    "category": "implementation",
                    "blocking": False
                },
                {
                    "id": "RULE.CORE.DELEGATION",
                    "title": "Core delegation rule",
                    "category": "delegation",
                    "blocking": False
                }
            ]
        }
        write_yaml(root / ".edison" / "rules" / "registry.yaml", core_registry)

        fastify_registry = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "RULE.FASTIFY.VALIDATION",
                    "title": "Fastify validation rule",
                    "category": "validation",
                    "blocking": False
                }
            ]
        }
        write_yaml(root / ".edison" / "packs" / "fastify" / "rules" / "registry.yaml", fastify_registry)

        prisma_registry = {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "RULE.prisma.VALIDATION",
                    "title": "prisma validation rule",
                    "category": "validation",
                    "blocking": False
                }
            ]
        }
        write_yaml(root / ".edison" / "packs" / "prisma" / "rules" / "registry.yaml", prisma_registry)

    def test_role_based_guideline_filtering(self, isolated_project_env: Path) -> None:
        """ZenAdapter.get_applicable_guidelines should filter by role."""
        root = isolated_project_env
        self._write_basic_config(root)
        self._write_guidelines(root)

        adapter = ZenAdapter(project_root=root)

        default_guides = adapter.get_applicable_guidelines("default")
        assert {"QUALITY", "security", "performance", "architecture"} <= set(default_guides)

        review_guides = adapter.get_applicable_guidelines("codereviewer")
        assert "QUALITY" in review_guides
        assert "security" in review_guides
        assert "performance" in review_guides
        assert "architecture" not in review_guides

        planner_guides = adapter.get_applicable_guidelines("planner")
        assert "architecture" in planner_guides
        assert "QUALITY" not in planner_guides

    def test_role_based_rule_filtering(self, isolated_project_env: Path) -> None:
        """ZenAdapter.get_applicable_rules should filter rule categories."""
        root = isolated_project_env
        self._write_basic_config(root)
        self._write_rules_registry(root)

        adapter = ZenAdapter(project_root=root)

        all_rules = adapter.get_applicable_rules("default")
        assert {r["id"] for r in all_rules} == {
            "RULE.REVIEW.VALIDATION",
            "RULE.REVIEW.IMPLEMENTATION",
            "RULE.PLANNING.DELEGATION",
            "RULE.PLANNING.SESSION",
        }

        review_rules = adapter.get_applicable_rules("codereviewer")
        review_ids = {r["id"] for r in review_rules}
        assert "RULE.REVIEW.VALIDATION" in review_ids
        assert "RULE.REVIEW.IMPLEMENTATION" in review_ids
        assert "RULE.PLANNING.DELEGATION" not in review_ids
        assert "RULE.PLANNING.SESSION" not in review_ids

        planning_rules = adapter.get_applicable_rules("planner")
        planning_ids = {r["id"] for r in planning_rules}
        assert "RULE.PLANNING.DELEGATION" in planning_ids
        assert "RULE.PLANNING.SESSION" in planning_ids
        assert "RULE.REVIEW.VALIDATION" not in planning_ids

    def test_config_driven_guideline_mapping_for_project_role(
        self, isolated_project_env: Path
    ) -> None:
        """Config-driven zen.roles should control guideline selection for project roles."""
        root = isolated_project_env
        self._write_config_with_project_roles(root)
        self._write_guidelines_with_packs_and_overlays(root)

        adapter = ZenAdapter(project_root=root)

        names = adapter.get_applicable_guidelines("project-api-builder")

        # Only guidelines matching configured patterns should be selected.
        assert "api-design" in names
        assert "validation" in names
        assert "error-handling" in names

        # Pack filter should include fastify guidelines but exclude prisma-only ones.
        assert "schema-validation" in names
        assert "schema-design" not in names

    def test_config_driven_rule_mapping_for_project_role(
        self, isolated_project_env: Path
    ) -> None:
        """Config-driven zen.roles.rules should filter by category and pack."""
        root = isolated_project_env
        self._write_config_with_project_roles(root)
        self._write_rules_with_packs(root)

        adapter = ZenAdapter(project_root=root)
        rules = adapter.get_applicable_rules("project-api-builder")
        ids = {r["id"] for r in rules}

        # Includes core validation + implementation rules
        assert "RULE.CORE.VALIDATION" in ids
        assert "RULE.CORE.IMPLEMENTATION" in ids

        # Includes validation rules from configured pack(s)
        assert "RULE.FASTIFY.VALIDATION" in ids

        # Excludes validation rules from packs not listed under role.packs
        assert "RULE.prisma.VALIDATION" not in ids

        # Excludes unrelated categories
        assert "RULE.CORE.DELEGATION" not in ids

    def test_compose_prompt_includes_role_sections(self, isolated_project_env: Path) -> None:
        """compose_zen_prompt should include model/role and role-specific sections."""
        root = isolated_project_env
        self._write_basic_config(root)
        self._write_guidelines(root)
        self._write_rules_registry(root)

        adapter = ZenAdapter(project_root=root)

        text = adapter.compose_zen_prompt(role="codereviewer", model="codex", packs=[])

        assert "Edison / Zen MCP Prompt" in text
        assert "Model: codex" in text
        assert "Role: codereviewer" in text

        # Role-specific guideline content should appear
        assert "QUALITY-GUIDE" in text
        assert "SECURITY-GUIDE" in text
        # Planner-only guideline should be excluded
        assert "ARCHITECTURE-GUIDE" not in text

    @pytest.mark.parametrize("model", ["codex", "claude", "gemini"])
    def test_model_specific_formatting(self, isolated_project_env: Path, model: str) -> None:
        """compose_zen_prompt should annotate prompts with model-specific hints."""
        root = isolated_project_env
        self._write_basic_config(root)
        self._write_guidelines(root)
        self._write_rules_registry(root)

        adapter = ZenAdapter(project_root=root)
        text = adapter.compose_zen_prompt(role="default", model=model, packs=[])

        assert f"Model: {model}" in text
        # Each model should have some context-window hint
        assert "Context window" in text
