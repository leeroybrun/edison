import re
import subprocess
from pathlib import Path
import pytest
from edison.data import get_data_path

pytestmark = pytest.mark.skip(reason="Documentation not yet written - guide files moved/pending")

# Doc doesn't exist yet - when added, it will be in bundled data
DOC_PATH = get_data_path("docs", "architecture/state-machine.md")


def _read_doc_text() -> str:
    assert DOC_PATH.exists(), (
        "state-machine.md must exist in bundled data (docs/architecture/state-machine.md)"
    )
    return DOC_PATH.read_text(encoding="utf-8")


def test_state_machine_doc_exists():
    """Doc must exist at the required path."""
    assert DOC_PATH.exists(), "Missing state-machine.md documentation file"


def test_required_sections_present():
    """Verify the doc contains all required top-level sections."""
    text = _read_doc_text()
    required_sections = [
        "Overview",
        "Session States",
        "State Transitions",
        "Timeout and Recovery",
        "File Operations",
        "Validation Gates",
        "Concurrent Session Handling",
        "Error Handling and Edge Cases",
        "Configuration",
        "Monitoring and Observability",
    ]
    missing = [s for s in required_sections if s not in text]
    assert not missing, f"Missing required sections: {missing}"


def test_all_states_documented():
    """Verify that all expected states are documented by name and directory hint."""
    text = _read_doc_text()
    # Expect directory notations like active/, closing/, validated/, recovery/, archived/
    for state in ["active/", "closing/", "validated/", "recovery/", "archived/"]:
        assert state in text, f"Expected to find state reference '{state}' in documentation"


def test_core_transitions_are_documented():
    """Verify that expected transitions are present in any supported arrow style."""
    text = _read_doc_text()

    def has_transition(src: str, dst: str) -> bool:
        patterns = [
            rf"\b{src}\s*→\s*{dst}\b",
            rf"\b{src}\s*->\s*{dst}\b",
            rf"\b{src}\s*-->\s*{dst}\b",
            rf"\b{src}\s*=>\s*{dst}\b",
        ]
        return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

    transitions = [
        ("active", "closing"),
        ("closing", "validated"),
        ("active", "recovery"),
        ("recovery", "active"),
        ("validated", "archived"),  # optional archive path
    ]

    missing = [(s, d) for (s, d) in transitions if not has_transition(s, d)]
    assert not missing, f"Missing transitions in doc: {missing}"

    # Also expect at least one Operations and one Rollback block in the doc
    assert "Operations" in text, "Expected an 'Operations' section describing file moves"
    assert "Rollback" in text, "Expected a 'Rollback' note for failure handling"


def test_timeout_and_recovery_section_is_present_and_actionable():
    """Ensure timeout workflow is documented with config knobs and recovery flow."""
    text = _read_doc_text()
    assert "Timeout and Recovery" in text
    # Must mention either hours-based (defaults) or threshold/checkInterval knobs
    has_hours = "session.timeout_hours" in text or "stale_check_interval_hours" in text
    has_threshold = "session:\n  timeout:" in text or "session.timeout.threshold" in text
    assert has_hours or has_threshold, (
        "Timeout config must mention either hours-based defaults or threshold/checkInterval"
    )
    # Recovery flow keywords
    for kw in ["recovery", "resume", "timeout", "preservation"]:
        assert kw.lower() in text.lower(), f"Missing timeout/recovery keyword: {kw}"


def test_configuration_snippets_are_valid_yaml_when_possible():
    """Collect fenced ```yaml blocks and validate they parse when PyYAML is available.

    Falls back to a lightweight structural check when PyYAML is not installed.
    """
    text = _read_doc_text()
    yaml_blocks = re.findall(r"```yaml\n(.*?)\n```", text, flags=re.DOTALL)
    assert yaml_blocks, "Expected at least one ```yaml fenced block in Configuration section"

    try:
        import yaml  # type: ignore
    except Exception:
        # Fallback check: ensure there is at least a 'session:' root key and indented children
        has_session_root = any(re.search(r"^session:\s*$", b, flags=re.MULTILINE) for b in yaml_blocks)
        assert has_session_root, "Configuration example must contain a 'session:' root key"
        return

    # Strong validation: every YAML block should parse
    for block in yaml_blocks:
        try:
            parsed = yaml.safe_load(block)
        except Exception as e:
            raise AssertionError(f"YAML block failed to parse: {e}\nBlock:\n{block}")
        assert isinstance(parsed, dict), "Top-level YAML should be a mapping"


def test_no_hardcoded_project_names():
    """Doc must be project-agnostic: no project-specific references."""
    text = _read_doc_text()
    import os

    configured = os.environ.get("PROJECT_NAME", "").strip().lower()
    extra = [
        t.strip().lower()
        for t in os.environ.get("PROJECT_TERMS", "").split(",")
        if t.strip()
    ]
    forbidden = [configured] if configured else []
    forbidden.extend(extra)
    # Provide a default sentinel so the test still asserts something without
    # hardcoding a specific project name.
    forbidden = [t for t in forbidden if t] or ["example-project"]

    found = [w for w in forbidden if w and w in text.lower()]
    assert not found, f"Doc contains project-specific references: {found}"
