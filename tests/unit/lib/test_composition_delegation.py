from __future__ import annotations

from edison.data import read_yaml


def test_composition_delegation_uses_yaml_file_pattern_rules() -> None:
    """
    Delegation config should be YAML-backed and tech-agnostic in core.

    Core delegation config must not contain stack-specific routing rules; packs/projects
    provide file-pattern routing rules via YAML overlays.
    """
    # Read delegation config directly from data
    delegation_cfg = read_yaml("config", "delegation.yaml")

    # Get file pattern rules from the config (under delegation.filePatternRules)
    file_pattern_rules = delegation_cfg.get("delegation", {}).get("filePatternRules", {})
    patterns = set(file_pattern_rules.keys())

    assert patterns == set(), f"Expected core delegation.filePatternRules to be empty, found: {patterns}"
