from __future__ import annotations

from pathlib import Path


def _repo_root_from_tests() -> Path:
    """Resolve repository root from the tests tree."""
    cur = Path(__file__).resolve()
    # .../example-project/.edison/core/tests/unit/lib/test_composition_delegation.py
    # parents[5] → repo root (example-project)
    return cur.parents[5]


def test_composition_delegation_uses_yaml_file_pattern_rules() -> None:
    """
    CompositionEngine._load_delegation_config should use YAML-backed config.

    Legacy JSON (.edison/core/delegation/config.json) defines only a couple of
    broad patterns like **/app/api/**, while the YAML config adds richer,
    more specific patterns such as **/route.ts. This test asserts that the
    composed delegation view reflects the YAML patterns and ignores the
    legacy JSON-only entries.
    """
    # Import core lib via tests sys.path wiring in conftest.py
    import edison.core.composition as composition  # type: ignore
    from edison.core.composition.orchestrator import load_delegation_config 
    repo_root = _repo_root_from_tests()
    engine = composition.CompositionEngine(repo_root=repo_root)  # type: ignore[call-arg]

    data = load_delegation_config(engine.config, engine.core_dir, engine.project_dir)
    patterns = {entry["pattern"] for entry in data.get("filePatternRules", [])}

    # YAML-only rule (present in .edison/core/config/delegation.yaml)
    assert "**/route.ts" in patterns
    # JSON-only rule (present in .edison/core/delegation/config.json)
    assert "**/app/api/**" not in patterns
