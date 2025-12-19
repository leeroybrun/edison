"""
Test suite for T-079: Next.js Metadata and Caching Rules.
"""
import pytest
import yaml
from pathlib import Path
from edison.data import get_data_path

class TestNextjsT079Rules:
    """Test Next.js Metadata and Caching rules."""

    @pytest.fixture
    def nextjs_registry(self) -> dict:
        """Load the Next.js rule registry."""
        registry_path = get_data_path("packs") / "nextjs" / "rules" / "registry.yml"
        with open(registry_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_metadata_rule_exists_and_valid(self, nextjs_registry: dict) -> None:
        """
        Verify RULE.NEXTJS.METADATA exists and meets requirements.

        Requirements:
        - id: RULE.NEXTJS.METADATA
        - title: "Metadata API Best Practices"
        - category: implementation
        - blocking: false
        - applies_to: [agent, validator]
        - sourcePath: packs/nextjs/guidelines/metadata.md
        - guidance: Cover static metadata export and dynamic generateMetadata
        """
        rules = {r["id"]: r for r in nextjs_registry["rules"]}
        rule_id = "RULE.NEXTJS.METADATA"

        assert rule_id in rules, f"{rule_id} is missing from registry"
        rule = rules[rule_id]

        assert rule["title"] == "Metadata API Best Practices"
        assert rule["category"] == "implementation"
        assert rule["blocking"] is False
        assert set(rule["applies_to"]) == {"agent", "validator"}
        assert rule["sourcePath"] == "packs/nextjs/guidelines/includes/nextjs/metadata.md"
        assert "metadata" in rule["guidance"].lower(), "Guidance should mention metadata"
        assert "generateMetadata" in rule["guidance"], "Guidance should mention generateMetadata"

    def test_caching_rule_exists_and_valid(self, nextjs_registry: dict) -> None:
        """
        Verify RULE.NEXTJS.CACHING exists and meets requirements.

        Requirements:
        - id: RULE.NEXTJS.CACHING
        - title: "Caching Strategies"
        - category: performance
        - blocking: false
        - applies_to: [agent, validator]
        - sourcePath: packs/nextjs/guidelines/caching.md
        - guidance: Cover revalidate, dynamic, cache tags, and fetch options
        """
        rules = {r["id"]: r for r in nextjs_registry["rules"]}
        rule_id = "RULE.NEXTJS.CACHING"

        assert rule_id in rules, f"{rule_id} is missing from registry"
        rule = rules[rule_id]

        assert rule["title"] == "Caching Strategies"
        assert rule["category"] == "performance"
        assert rule["blocking"] is False
        assert set(rule["applies_to"]) == {"agent", "validator"}
        assert rule["sourcePath"] == "packs/nextjs/guidelines/includes/nextjs/caching.md"
        
        guidance = rule["guidance"].lower()
        assert "revalidate" in guidance, "Guidance should mention revalidate"
        assert "dynamic" in guidance, "Guidance should mention dynamic"
        assert "cache" in guidance, "Guidance should mention cache"
        # The prompt asks to cover fetch options, checking for 'fetch' seems reasonable
        assert "fetch" in guidance, "Guidance should mention fetch"
