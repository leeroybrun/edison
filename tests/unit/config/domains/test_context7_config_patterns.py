"""Tests for Context7 config triggers and aliases loading."""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config.domains.context7 import Context7Config
from edison.data import read_yaml


@pytest.fixture()
def context7_config() -> Context7Config:
    # Default config (core only) is expected to be tech-agnostic and may be empty.
    return Context7Config()


def test_triggers_section_exists() -> None:
    """Verify triggers section exists in context7.yaml."""
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    assert "triggers" in section, "context7.yaml must contain 'triggers' section under 'context7'"
    assert isinstance(section["triggers"], dict), "triggers must be a dict"


def test_aliases_section_exists() -> None:
    """Verify aliases section exists in context7.yaml."""
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    assert "aliases" in section, "context7.yaml must contain 'aliases' section under 'context7'"
    assert isinstance(section["aliases"], dict), "aliases must be a dict"


def test_triggers_have_expected_packages() -> None:
    """Core triggers are intentionally empty (tech-agnostic).

    Packs provide technology-specific triggers.
    """
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    triggers = section.get("triggers", {})
    assert triggers == {}


def test_triggers_have_valid_patterns() -> None:
    """Verify each trigger has valid glob patterns."""
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    triggers = section.get("triggers", {})

    for pkg, patterns in triggers.items():
        assert isinstance(patterns, list), f"Triggers for '{pkg}' must be a list"
        # Core triggers may be empty; packs provide non-empty triggers.
        for pat in patterns:
            assert isinstance(pat, str), f"Pattern in '{pkg}' triggers must be string"
            assert pat.strip(), f"Pattern in '{pkg}' triggers must not be empty string"


def test_aliases_have_expected_mappings() -> None:
    """Core aliases are intentionally empty (tech-agnostic).

    Packs provide technology-specific aliases.
    """
    cfg = read_yaml("config", "context7.yaml")
    section = cfg.get("context7", {})
    aliases = section.get("aliases", {})
    assert aliases == {}


def test_context7_config_loads_triggers(context7_config: Context7Config) -> None:
    """Verify Context7Config.triggers loads from config."""
    triggers = context7_config.triggers
    assert isinstance(triggers, dict)
    # Core-only is tech-agnostic; triggers may be empty.


def test_context7_config_loads_aliases(context7_config: Context7Config) -> None:
    """Verify Context7Config.aliases loads from config."""
    aliases = context7_config.aliases
    assert isinstance(aliases, dict)
    # Core-only is tech-agnostic; aliases may be empty.


def test_get_triggers_method() -> None:
    """Verify Context7Config.get_triggers() works."""
    config = Context7Config()
    triggers = config.get_triggers()
    assert isinstance(triggers, dict)


def test_get_aliases_method() -> None:
    """Verify Context7Config.get_aliases() works."""
    config = Context7Config()
    aliases = config.get_aliases()
    assert isinstance(aliases, dict)


def test_context7_config_merges_pack_triggers_and_aliases(tmp_path: Path) -> None:
    """When packs are enabled, Context7Config must expose their triggers/aliases/packages."""
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)

    # Enable packs that contribute Context7 config.
    packs_yml = tmp_path / ".edison" / "config" / "packs.yml"
    packs_yml.write_text(
        "packs:\n  active:\n    - react\n    - nextjs\n    - prisma\n    - zod\n",
        encoding="utf-8",
    )

    cfg = Context7Config(repo_root=tmp_path)
    triggers = cfg.get_triggers()
    aliases = cfg.get_aliases()
    packages = cfg.get_packages()

    for key in ("react", "next", "prisma", "zod"):
        assert key in triggers
        assert key in packages

    # One representative alias from each pack
    assert aliases.get("react-dom") == "react"
    assert aliases.get("next/router") == "next"
    assert aliases.get("@prisma/client") == "prisma"
