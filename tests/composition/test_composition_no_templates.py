from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
core_path = ROOT / ".edison" / "core"
if str(core_path) not in sys.path:

from edison.core.composition import CompositionEngine 
def test_composition_works_without_templates_dir() -> None:
    """CompositionEngine must not depend on a validators/templates directory."""
    engine = CompositionEngine(repo_root=ROOT)
    results = engine.compose_validators()

    assert "codex-global" in results
    assert "claude-global" in results
    for res in results.values():
        assert res.cache_path is not None
        assert res.cache_path.exists()
