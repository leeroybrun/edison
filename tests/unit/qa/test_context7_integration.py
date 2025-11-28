"""Integration tests for context7.py config loading."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from edison.core.qa.context7 import _normalize, _merge_triggers, _load_triggers, _load_aliases


def test_load_triggers_returns_dict():
    """Verify _load_triggers returns a dict with expected structure."""
    triggers = _load_triggers()
    assert isinstance(triggers, dict)
    assert len(triggers) > 0
    assert all(isinstance(k, str) for k in triggers.keys())
    assert all(isinstance(v, list) for v in triggers.values())


def test_load_aliases_returns_dict():
    """Verify _load_aliases returns a dict with expected structure."""
    aliases = _load_aliases()
    assert isinstance(aliases, dict)
    assert len(aliases) > 0
    assert all(isinstance(k, str) for k in aliases.keys())
    assert all(isinstance(v, str) for v in aliases.values())


def test_normalize_uses_loaded_aliases():
    """Verify _normalize uses config-loaded aliases."""
    # Test known aliases from config
    assert _normalize("react-dom") == "react"
    assert _normalize("nextjs") == "next"
    assert _normalize("next/router") == "next"
    assert _normalize("@prisma/client") == "prisma"
    assert _normalize("prisma-client") == "prisma"

    # Test normalization of unknown package
    assert _normalize("unknown-package") == "unknown-package"

    # Test case sensitivity
    assert _normalize("React-Dom") == "react"
    assert _normalize("NEXTJS") == "next"


def test_merge_triggers_uses_loaded_config():
    """Verify _merge_triggers uses config-loaded triggers."""
    # Empty validator config
    result = _merge_triggers({})
    assert isinstance(result, dict)
    assert "react" in result
    assert "next" in result
    assert "zod" in result
    assert "prisma" in result

    # Check specific patterns match config
    assert "*.tsx" in result["react"]
    assert "app/**/*" in result["next"]


def test_merge_triggers_merges_validator_overrides():
    """Verify _merge_triggers merges validator config overrides."""
    validator_config = {
        "postTrainingPackages": {
            "react": {
                "triggers": ["custom-pattern.tsx"]
            }
        }
    }

    result = _merge_triggers(validator_config)

    # Should contain both config patterns and validator override
    assert "*.tsx" in result["react"]  # From config
    assert "custom-pattern.tsx" in result["react"]  # From validator override


def test_merge_triggers_handles_new_packages_from_validator():
    """Verify _merge_triggers can add new packages from validator config."""
    validator_config = {
        "postTrainingPackages": {
            "new-package": {
                "triggers": ["pattern1.ts", "pattern2.ts"]
            }
        }
    }

    result = _merge_triggers(validator_config)

    # Should include the new package
    assert "new-package" in result
    assert result["new-package"] == ["pattern1.ts", "pattern2.ts"]


def test_merge_triggers_deduplicates_patterns():
    """Verify _merge_triggers removes duplicate patterns."""
    validator_config = {
        "postTrainingPackages": {
            "react": {
                "triggers": ["*.tsx", "*.tsx", "custom.tsx"]  # Duplicate *.tsx
            }
        }
    }

    result = _merge_triggers(validator_config)

    # Should deduplicate *.tsx
    tsx_count = result["react"].count("*.tsx")
    assert tsx_count == 1, "Duplicate patterns should be removed"
