"""Tests for Zen prompt composition."""
from __future__ import annotations

import os
from pathlib import Path

from edison.core.composition import CompositionEngine
from edison.core.composition.formatting import compose_for_role

# For tests that need a repo root reference
ROOT = Path(__file__).resolve().parent.parent


def test_zen_composition_basic(tmp_path: Path):
    """Test basic Zen prompt generation."""
    config = {
        "project": {"name": "test-project"},
        "zen": {"roles": ["codex"], "enabled": True},
        "packs": {"active": []},
    }

    engine = CompositionEngine(config, repo_root=ROOT)
    results = engine.compose_zen_prompts(tmp_path)

    assert "codex" in results
    assert results["codex"].exists()
    content = results["codex"].read_text(encoding="utf-8")
    assert "===" in content  # Zen heading format simplification


def test_zen_includes_rules(tmp_path: Path):
    """Test Zen prompts include rules context when enabled."""
    config = {
        "rules": {
            "enforcement": True,
            "byState": {
                "done": [
                    {
                        "id": "tests-pass",
                        "description": "Tests must pass",
                        "blocking": True,
                    }
                ]
            },
        },
        "zen": {"roles": ["codex"]},
        "packs": {"active": []},
    }

    engine = CompositionEngine(config, repo_root=ROOT)
    content = compose_for_role(engine, "codex")

    assert "Project Rules" in content
    assert "Tests must pass" in content
    assert "🔴 BLOCKING" in content
