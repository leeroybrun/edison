"""Tests for Context7 config triggers and aliases loading."""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config.domains.context7 import Context7Config, load_triggers, load_aliases
from edison.data import read_yaml


@pytest.fixture()
def context7_config() -> Context7Config:
    return Context7Config()


def test_triggers_section_exists() -> None:
    """Verify triggers section exists in context7.yml."""
    cfg = read_yaml("config", "context7.yml")
    assert "triggers" in cfg, "context7.yml must contain 'triggers' section"
    assert isinstance(cfg["triggers"], dict), "triggers must be a dict"


def test_aliases_section_exists() -> None:
    """Verify aliases section exists in context7.yml."""
    cfg = read_yaml("config", "context7.yml")
    assert "aliases" in cfg, "context7.yml must contain 'aliases' section"
    assert isinstance(cfg["aliases"], dict), "aliases must be a dict"


def test_triggers_have_expected_packages() -> None:
    """Verify triggers contain expected package names."""
    cfg = read_yaml("config", "context7.yml")
    triggers = cfg.get("triggers", {})
    expected = {"react", "next", "zod", "prisma"}
    missing = expected.difference(triggers.keys())
    assert not missing, f"Missing expected trigger packages: {sorted(missing)}"


def test_triggers_have_valid_patterns() -> None:
    """Verify each trigger has valid glob patterns."""
    cfg = read_yaml("config", "context7.yml")
    triggers = cfg.get("triggers", {})

    for pkg, patterns in triggers.items():
        assert isinstance(patterns, list), f"Triggers for '{pkg}' must be a list"
        assert patterns, f"Triggers for '{pkg}' must not be empty"
        for pat in patterns:
            assert isinstance(pat, str), f"Pattern in '{pkg}' triggers must be string"
            assert pat.strip(), f"Pattern in '{pkg}' triggers must not be empty string"


def test_aliases_have_expected_mappings() -> None:
    """Verify aliases contain expected mappings."""
    cfg = read_yaml("config", "context7.yml")
    aliases = cfg.get("aliases", {})

    expected_mappings = {
        "react-dom": "react",
        "nextjs": "next",
        "next/router": "next",
        "@prisma/client": "prisma",
        "prisma-client": "prisma",
    }

    for alias, canonical in expected_mappings.items():
        assert alias in aliases, f"Missing expected alias '{alias}'"
        assert aliases[alias] == canonical, f"Alias '{alias}' should map to '{canonical}'"


def test_context7_config_loads_triggers(context7_config: Context7Config) -> None:
    """Verify Context7Config.triggers loads from config."""
    triggers = context7_config.triggers
    assert isinstance(triggers, dict)
    assert "react" in triggers
    assert "next" in triggers
    assert isinstance(triggers["react"], list)
    assert len(triggers["react"]) > 0


def test_context7_config_loads_aliases(context7_config: Context7Config) -> None:
    """Verify Context7Config.aliases loads from config."""
    aliases = context7_config.aliases
    assert isinstance(aliases, dict)
    assert "react-dom" in aliases
    assert aliases["react-dom"] == "react"


def test_load_triggers_helper() -> None:
    """Verify load_triggers() module function works."""
    triggers = load_triggers()
    assert isinstance(triggers, dict)
    assert "react" in triggers
    assert "next" in triggers


def test_load_aliases_helper() -> None:
    """Verify load_aliases() module function works."""
    aliases = load_aliases()
    assert isinstance(aliases, dict)
    assert "react-dom" in aliases
    assert aliases["react-dom"] == "react"


def test_triggers_match_hardcoded_defaults() -> None:
    """Verify config triggers match the original hardcoded DEFAULT_TRIGGERS."""
    triggers = load_triggers()

    # Original hardcoded values
    expected_react = ["*.tsx", "*.jsx", "**/components/**/*"]
    expected_next = ["app/**/*", "**/route.ts", "**/layout.tsx", "**/page.tsx"]
    expected_zod = ["**/*.schema.ts", "**/*.validation.ts", "**/*schema.ts"]
    expected_prisma = [
        "**/*.prisma",
        "**/prisma/schema.*",
        "**/prisma/migrations/**/*",
        "**/prisma/seeds/**/*",
    ]

    assert triggers["react"] == expected_react
    assert triggers["next"] == expected_next
    assert triggers["zod"] == expected_zod
    assert triggers["prisma"] == expected_prisma


def test_aliases_match_hardcoded_defaults() -> None:
    """Verify config aliases match the original hardcoded ALIASES."""
    aliases = load_aliases()

    # Original hardcoded values
    expected = {
        "react-dom": "react",
        "next/router": "next",
        "nextjs": "next",
        "@prisma/client": "prisma",
        "prisma-client": "prisma",
    }

    assert aliases == expected
