"""Tests for Zen prompt composition."""
from __future__ import annotations

from pathlib import Path
import sys
import os

# Add Edison core lib to sys.path similar to other tests
ROOT = Path(__file__).resolve().parents[3]  # repository root
CORE_PATH = ROOT / ".edison" / "core"
if str(CORE_PATH) not in sys.path:
# Ensure repo resolution prefers the outer project root when running inside the nested .edison repo.
os.environ.setdefault("AGENTS_PROJECT_ROOT", str(ROOT))

from edison.core.composition import CompositionEngine 
from edison.core.composition.formatting import compose_for_role 
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
