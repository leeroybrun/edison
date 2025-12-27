"""
Test pack-specific rule registries (T-032).

This test suite validates that each pack can define its own rules registry
and that the composition engine correctly loads and merges pack rules with core rules.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from edison.core.rules import RulesRegistry, compose_rules


class TestPackSpecificRegistries:
    """Test pack-specific rule registries functionality."""

    def test_load_pack_registry_iterates_all_pack_roots(
        self,
        isolated_project_env: Path,
    ) -> None:
        """RulesRegistry.load_pack_registry() must iterate pack roots, not hard-code 3 paths.

        This enables future N-layer pack roots without duplicating rules loading logic.
        """
        root = isolated_project_env
        registry = RulesRegistry(project_root=root)

        pack_name = "custompack"
        extra_root = root / "extra-pack-root"
        extra_registry = extra_root / pack_name / "rules" / "registry.yml"
        extra_registry.parent.mkdir(parents=True, exist_ok=True)
        with open(extra_registry, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {
                    "version": "9.9.9",
                    "rules": [
                        {
                            "id": "RULE.EXTRA.PACK_ROOT",
                            "title": "Extra pack root rule",
                            "category": "implementation",
                            "blocking": False,
                            "applies_to": ["agent"],
                            "guidance": "Loaded from an extra pack root.",
                        }
                    ],
                },
                f,
                sort_keys=False,
            )

        from edison.core.packs.paths import PackRoot

        # Insert an extra root between bundled and user to ensure load_pack_registry
        # truly iterates roots rather than relying on fixed attributes.
        registry._pack_roots = (  # type: ignore[attr-defined]
            registry._pack_roots[0],  # type: ignore[index]
            PackRoot(kind="extra", path=extra_root),
            *registry._pack_roots[1:],  # type: ignore[index]
        )

        merged = registry.load_pack_registry(pack_name)
        ids = {r.get("id") for r in (merged.get("rules") or []) if isinstance(r, dict)}
        assert "RULE.EXTRA.PACK_ROOT" in ids

    def test_nextjs_pack_has_rule_registry(self) -> None:
        """
        Test that nextjs pack has a rules/registry.yml file.

        Validates:
        - File exists at correct location
        - Contains valid YAML structure
        - Rules have applies_to field
        """
        from edison.data import get_data_path

        nextjs_registry_path = get_data_path("packs") / "nextjs" / "rules" / "registry.yml"

        assert nextjs_registry_path.exists(), (
            f"nextjs pack should have rules/registry.yml at {nextjs_registry_path}"
        )

        # Validate YAML structure
        with open(nextjs_registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), "registry.yml should be a YAML mapping"
        assert "version" in data, "registry.yml should have version field"
        assert "rules" in data, "registry.yml should have rules field"
        assert isinstance(data["rules"], list), "rules field should be a list"

        # Validate each rule has applies_to field
        for rule in data["rules"]:
            assert "id" in rule, f"Rule missing id field: {rule}"
            assert "applies_to" in rule, f"Rule {rule['id']} missing applies_to field"
            assert isinstance(rule["applies_to"], list), (
                f"Rule {rule['id']} applies_to should be a list"
            )
            # At least one valid role
            valid_roles = {"orchestrator", "agent", "validator"}
            assert any(role in valid_roles for role in rule["applies_to"]), (
                f"Rule {rule['id']} must have at least one valid role in applies_to"
            )

    def test_react_pack_has_rule_registry(self) -> None:
        """Test that react pack has a rules/registry.yml file."""
        from edison.data import get_data_path

        react_registry_path = get_data_path("packs") / "react" / "rules" / "registry.yml"

        assert react_registry_path.exists(), (
            f"react pack should have rules/registry.yml at {react_registry_path}"
        )

        # Validate YAML structure
        with open(react_registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), "registry.yml should be a YAML mapping"
        assert "version" in data, "registry.yml should have version field"
        assert "rules" in data, "registry.yml should have rules field"

        # Validate applies_to on all rules
        for rule in data["rules"]:
            assert "applies_to" in rule, f"Rule {rule.get('id')} missing applies_to field"

    def test_prisma_pack_has_rule_registry(self) -> None:
        """Test that prisma pack has a rules/registry.yml file."""
        from edison.data import get_data_path

        prisma_registry_path = get_data_path("packs") / "prisma" / "rules" / "registry.yml"

        assert prisma_registry_path.exists(), (
            f"prisma pack should have rules/registry.yml at {prisma_registry_path}"
        )

        # Validate YAML structure
        with open(prisma_registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), "registry.yml should be a YAML mapping"
        assert "version" in data, "registry.yml should have version field"
        assert "rules" in data, "registry.yml should have rules field"

        # Validate applies_to on all rules
        for rule in data["rules"]:
            assert "applies_to" in rule, f"Rule {rule.get('id')} missing applies_to field"

    def test_tailwind_pack_has_rule_registry(self) -> None:
        """Test that tailwind pack has a rules/registry.yml file."""
        from edison.data import get_data_path

        tailwind_registry_path = get_data_path("packs") / "tailwind" / "rules" / "registry.yml"

        assert tailwind_registry_path.exists(), (
            f"tailwind pack should have rules/registry.yml at {tailwind_registry_path}"
        )

        # Validate YAML structure
        with open(tailwind_registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), "registry.yml should be a YAML mapping"
        assert "version" in data, "registry.yml should have version field"
        assert "rules" in data, "registry.yml should have rules field"

        # Validate applies_to on all rules
        for rule in data["rules"]:
            assert "applies_to" in rule, f"Rule {rule.get('id')} missing applies_to field"

    def test_tailwind_pack_has_detailed_v4_rules(self) -> None:
        """Tailwind pack must expose the full v4 rule set (syntax, tokens, cache, PostCSS)."""
        from edison.data import get_data_path

        registry_path = get_data_path("packs") / "tailwind" / "rules" / "registry.yml"
        assert registry_path.exists(), "Tailwind rules registry is missing"

        with open(registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = {rule["id"]: rule for rule in data.get("rules", [])}

        expected_rules = {
            "RULE.TAILWIND.V4_SYNTAX",
            "RULE.TAILWIND.FONT_SANS_REQUIRED",
            "RULE.TAILWIND.ARBITRARY_VALUES_FOR_THEME",
            "RULE.TAILWIND.CLEAR_CACHE_AFTER_CSS_CHANGES",
            "RULE.TAILWIND.POSTCSS_V4_PLUGIN",
            "RULE.TAILWIND.THEME_TOKENS_IN_CSS",
        }

        missing = expected_rules - set(rules)
        assert not missing, f"Tailwind v4 detailed rules missing from registry: {sorted(missing)}"

        assert '@import "tailwindcss"' in rules["RULE.TAILWIND.V4_SYNTAX"]["guidance"], (
            "v4 syntax rule should mention CSS @import directive"
        )
        assert "font-sans" in rules["RULE.TAILWIND.FONT_SANS_REQUIRED"]["guidance"], (
            "font-sans rule should call out explicit font usage"
        )
        assert "arbitrary" in rules["RULE.TAILWIND.ARBITRARY_VALUES_FOR_THEME"]["guidance"], (
            "arbitrary values guidance should be present"
        )
        assert ".next" in rules["RULE.TAILWIND.CLEAR_CACHE_AFTER_CSS_CHANGES"]["guidance"], (
            "cache clearing rule should mention .next cache"
        )
        assert "@tailwindcss/postcss" in rules["RULE.TAILWIND.POSTCSS_V4_PLUGIN"]["guidance"], (
            "PostCSS rule should reference @tailwindcss/postcss"
        )
        assert "@theme" in rules["RULE.TAILWIND.THEME_TOKENS_IN_CSS"]["guidance"], (
            "theme tokens rule should reference @theme directive"
        )

    def test_pack_rules_compose_with_core_rules(
        self,
        isolated_project_env: Path,
    ) -> None:
        """
        Test that pack rules are correctly composed with core rules.

        Validates:
        - Pack rules are loaded by RulesRegistry
        - Pack rules merge with core rules
        - applies_to field is preserved in composed output
        """
        root = isolated_project_env

        # Create nextjs pack registry
        nextjs_registry = root / ".edison" / "packs" / "nextjs" / "rules" / "registry.yml"
        nextjs_registry.parent.mkdir(parents=True, exist_ok=True)
        with open(nextjs_registry, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "RULE.NEXTJS.SERVER_FIRST",
                        "title": "Server Components by Default",
                        "category": "implementation",
                        "blocking": False,
                        "applies_to": ["agent"],
                        "guidance": "Use Server Components unless client interactivity needed.",
                    }
                ],
            }, f, sort_keys=False)

        # Compose rules with nextjs pack
        registry = RulesRegistry(project_root=root)
        result = registry.compose(packs=["nextjs"])

        # Verify both core and pack rules are present
        rules = result["rules"]
        assert "RULE.DELEGATION.PRIORITY_CHAIN" in rules, "Core rule should be present"
        assert "RULE.NEXTJS.SERVER_FIRST" in rules, "Pack rule should be present"

        # Verify pack rule has correct metadata
        nextjs_rule = rules["RULE.NEXTJS.SERVER_FIRST"]
        assert nextjs_rule["title"] == "Server Components by Default"
        assert nextjs_rule["category"] == "implementation"
        assert "pack:nextjs" in nextjs_rule["origins"]

    def test_pack_rules_follow_same_schema_as_core_rules(self) -> None:
        """
        Test that pack rules follow the same schema as core rules.

        Validates all pack registries use consistent structure with core registry.
        """
        from edison.data import get_data_path

        # Load core registry schema
        core_registry_path = get_data_path("rules", "registry.yml")
        with open(core_registry_path, encoding="utf-8") as f:
            core_data = yaml.safe_load(f)

        # Get a sample core rule to understand the schema
        core_rules = core_data.get("rules", [])
        assert len(core_rules) > 0, "Core registry should have at least one rule"

        core_rule_keys = set(core_rules[0].keys())
        required_keys = {"id", "title", "category", "blocking", "applies_to"}

        # Check each pack registry
        pack_names = ["nextjs", "react", "prisma", "tailwind"]

        for pack_name in pack_names:
            pack_registry_path = get_data_path("packs") / pack_name / "rules" / "registry.yml"

            if not pack_registry_path.exists():
                continue

            with open(pack_registry_path, encoding="utf-8") as f:
                pack_data = yaml.safe_load(f)

            pack_rules = pack_data.get("rules", [])

            for rule in pack_rules:
                rule_keys = set(rule.keys())

                # Verify required keys are present
                missing_keys = required_keys - rule_keys
                assert not missing_keys, (
                    f"Pack {pack_name} rule {rule.get('id')} missing required keys: {missing_keys}"
                )

    def test_composition_engine_loads_pack_rules(self) -> None:
        """
        Test that the composition engine correctly loads pack rules via RulesRegistry.

        Validates that pack registries can be loaded without errors.
        """
        from edison.data import get_data_path

        # Verify each pack registry can be loaded by RulesRegistry
        packs = ["nextjs", "react", "prisma", "tailwind"]

        for pack_name in packs:
            pack_registry_path = get_data_path("packs") / pack_name / "rules" / "registry.yml"

            # Verify file exists
            assert pack_registry_path.exists(), (
                f"Pack {pack_name} should have rules registry at {pack_registry_path}"
            )

            # Verify it can be loaded as YAML
            with open(pack_registry_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Verify structure
            assert "version" in data, f"Pack {pack_name} registry should have version"
            assert "rules" in data, f"Pack {pack_name} registry should have rules"
            assert isinstance(data["rules"], list), (
                f"Pack {pack_name} registry rules should be a list"
            )

            # Verify at least one rule has pack-specific ID
            rule_ids = [rule.get("id", "") for rule in data["rules"]]
            assert len(rule_ids) > 0, f"Pack {pack_name} should have at least one rule"

            # Verify pack-specific rule ID patterns
            expected_prefix = f"RULE.{pack_name.upper()}"
            pack_specific_rules = [rid for rid in rule_ids if rid.startswith(expected_prefix)]
            assert len(pack_specific_rules) > 0, (
                f"Pack {pack_name} should have at least one rule with ID starting with {expected_prefix}"
            )

    def test_pack_rules_have_appropriate_applies_to_values(self) -> None:
        """
        Test that pack rules have appropriate applies_to values.

        Validates:
        - applies_to is always a list
        - Contains only valid roles: orchestrator, agent, validator
        - At least one role is specified
        """
        from edison.data import get_data_path

        pack_names = ["nextjs", "react", "prisma", "tailwind"]
        valid_roles = {"orchestrator", "agent", "validator"}

        for pack_name in pack_names:
            pack_registry_path = get_data_path("packs") / pack_name / "rules" / "registry.yml"

            if not pack_registry_path.exists():
                continue

            with open(pack_registry_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            rules = data.get("rules", [])

            for rule in rules:
                rule_id = rule.get("id", "unknown")
                applies_to = rule.get("applies_to", [])

                # Must be a list
                assert isinstance(applies_to, list), (
                    f"Pack {pack_name} rule {rule_id}: applies_to must be a list"
                )

                # Must have at least one role
                assert len(applies_to) > 0, (
                    f"Pack {pack_name} rule {rule_id}: applies_to must have at least one role"
                )

                # All roles must be valid
                for role in applies_to:
                    assert role in valid_roles, (
                        f"Pack {pack_name} rule {rule_id}: invalid role '{role}' in applies_to. "
                        f"Valid roles: {valid_roles}"
                    )
