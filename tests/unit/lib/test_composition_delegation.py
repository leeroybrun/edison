from __future__ import annotations

from edison.data import read_yaml


def test_composition_delegation_uses_yaml_file_pattern_rules() -> None:
    """
    Delegation config should use YAML-backed config with specific patterns.

    The YAML config includes specific patterns such as **/route.ts for API routes.
    This test asserts that the delegation config contains these patterns.
    """
    # Read delegation config directly from data
    delegation_cfg = read_yaml("config", "delegation.yaml")

    # Get file pattern rules from the config (under delegation.filePatternRules)
    file_pattern_rules = delegation_cfg.get("delegation", {}).get("filePatternRules", {})
    patterns = set(file_pattern_rules.keys())

    # YAML rule (present in data/config/delegation.yaml)
    assert "**/route.ts" in patterns, f"Expected **/route.ts in patterns, found: {patterns}"
