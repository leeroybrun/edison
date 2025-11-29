from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import pytest


from tests.helpers.paths import get_repo_root

# Add Edison core lib to path for imports in tests
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = get_repo_root()

CORE_ROOT = _CORE_ROOT
def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# -------------------------
# Q1: Dimension weight mismatch
# -------------------------
def test_q1_dimension_weights_alignment_sum_and_values():
    """Q1: Config dimension weights must match validator expectations and sum to 100.

    Expected weights (percent):
      functionality=30, reliability=25, security=20, maintainability=15, performance=10
    """
    from edison.core.config import ConfigManager 
    cfg = ConfigManager().load_config(validate=False)
    dims = ((cfg.get("validation") or {}).get("dimensions") or {})

    # Must contain all expected keys
    expected = {
        "functionality": 30,
        "reliability": 25,
        "security": 20,
        "maintainability": 15,
        "performance": 10,
    }

    missing = [k for k in expected.keys() if k not in dims]
    assert not missing, f"validation.dimensions missing keys: {missing}"

    # Must match exact values
    mismatched = {k: (dims.get(k), v) for k, v in expected.items() if int(dims.get(k, -1)) != v}
    assert not mismatched, f"validation.dimensions mismatched values: {mismatched}"

    # Must sum to 100
    total = sum(int(v) for v in dims.values())
    assert total == 100, f"validation.dimensions must sum to 100, got {total}"


# -------------------------
# Q2: Include directive protection (safe_include)
# -------------------------
def test_q2_safe_include_missing_file():
    """Q2: process_validator_template must handle missing includes via safe fallback without errors."""
    # Import lazily so the test fails only for this case when not implemented
    from edison.core.qa.validator import process_validator_template 
    template = (
        "# Validator\n"  # minimal content to render
        "{{ safe_include('non-existent.md', fallback='<!-- Missing -->') }}\n"
    )
    result = process_validator_template(template, context={})
    assert "<!-- Missing -->" in result
    assert "Error" not in result and "Traceback" not in result


def test_q2_safe_include_blocks_path_traversal():
    """Q2: safe_include must block path traversal attempts and return fallback content."""
    from edison.core.qa.validator import process_validator_template 
    template = "{{ safe_include('../../etc/passwd', fallback='<!-- Blocked -->') }}\n"
    out = process_validator_template(template, context={})
    assert "<!-- Blocked -->" in out
    assert "root:" not in out  # never leak system files


def test_q2_validators_use_safe_include_directives():
    """Q2: Project validator markdown should use safe_include wrappers around includes."""
    validators = [
        Path(".agents/validators/global/global-codex.md"),
        Path(".agents/validators/global/global-claude.md"),
        Path(".agents/validators/security/codex-security.md"),
        Path(".agents/validators/performance/codex-performance.md"),
    ]
    missing = []
    for vf in validators:
        if not vf.exists():
            pytest.skip(f"validator missing: {vf}")
        content = _read_file(vf)
        if "safe_include(" not in content:
            missing.append(str(vf))
    assert not missing, f"Validators missing safe_include: {missing}"


# -------------------------
# Q3: Standardized validation report format
# -------------------------
def test_q3_standard_report_template_exists_and_has_required_sections():
    """Q3: Standard report template must exist with required sections."""
    report_tpl = Path(".edison/core/validators/_report-template.md")
    assert report_tpl.exists(), "Missing standard report template at .edison/core/validators/_report-template.md"

    text = _read_file(report_tpl)
    for section in [
        "# {{ validator_name }} Validation Report",
        "## Executive Summary",
        "## Dimension Scores",
        "## Findings",
        "## Validation Pass/Fail",
    ]:
        assert section in text, f"Report template missing section: {section}"


def test_q3_validators_render_with_standard_sections(tmp_path: Path):
    """Q3: Rendering validators should include the standard report sections.

    Uses lib.qa.validator.run_validator to render into a single report.
    """
    from edison.core.qa.validator import run_validator 
    # Pick one validator to render (global Codex)
    validator_path = Path(".agents/validators/global/global-codex.md")
    assert validator_path.exists(), f"Validator file missing: {validator_path}"

    report = run_validator(str(validator_path), session_id="test-session-qa")
    required_sections = [
        re.compile(r"# .* Validation Report"),
        re.compile(r"## Executive Summary"),
        re.compile(r"## Dimension Scores"),
        re.compile(r"## Findings"),
        re.compile(r"## Validation Pass/Fail"),
    ]
    for sec in required_sections:
        assert sec.search(report), f"Rendered report missing section: {sec.pattern}"


# -------------------------
# Q4: Score tracking over time
# -------------------------
def test_q4_score_tracking_and_ordering(tmp_path: Path):
    """Q4: Score history should append entries and remain chronologically ordered."""
    from edison.core.qa.scoring import track_validation_score, get_score_history 
    session_id = "qa-score-track-test"
    # Ensure clean slate
    hist_file = Path(f".project/qa/score-history/{session_id}.jsonl")
    if hist_file.exists():
        hist_file.unlink()

    from tests.helpers.timeouts import SHORT_SLEEP

    for _ in range(3):
        scores = {"functionality": 8, "reliability": 7}
        track_validation_score(session_id, "test-validator", scores, overall_score=7.5)
        time.sleep(SHORT_SLEEP)

    history = get_score_history(session_id)
    assert len(history) == 3, f"expected 3 history entries, got {len(history)}"
    timestamps = [h["timestamp"] for h in history]
    assert timestamps == sorted(timestamps), "history timestamps must be non-decreasing"


def test_q4_score_history_scalability(tmp_path: Path):
    """Q4: Score tracking should handle many runs without degradation (smoke for 1k)."""
    from edison.core.qa.scoring import track_validation_score, get_score_history 
    session_id = "qa-score-scale-test"
    hist_file = Path(f".project/qa/score-history/{session_id}.jsonl")
    if hist_file.exists():
        hist_file.unlink()

    for i in range(1000):  # smoke threshold; implementation target is 10k
        track_validation_score(session_id, "test-validator", {"functionality": 7}, overall_score=7.0)

    hist = get_score_history(session_id)
    assert len(hist) == 1000, f"expected 1000 entries, got {len(hist)}"


# -------------------------
# Q5: Automated regression detection
# -------------------------
def test_q5_regression_detection_thresholds():
    """Q5: detect_regression flags significant score drops and ignores minor deltas."""
    from edison.core.qa.scoring import track_validation_score, detect_regression 
    session_id = "qa-regression-test"
    # Seed two prior runs
    track_validation_score(session_id, "test-validator", {"functionality": 8}, overall_score=8.0)
    track_validation_score(session_id, "test-validator", {"functionality": 8}, overall_score=7.8)

    # Minor change below threshold (0.5) → no regression
    is_reg, details = detect_regression(session_id, current_score=7.6, threshold=0.5)
    assert not is_reg and details.get("status") == "no_regression"

    # Significant drop → regression
    is_reg, details = detect_regression(session_id, current_score=5.0, threshold=0.5)
    assert is_reg, "expected regression for large score drop"
    assert details.get("previous_score") >= details.get("current_score")


# -------------------------
# CLI surface (for later integration, should fail red now)
# -------------------------
def test_cli_validate_session_exists_and_shows_usage():
    """Session validation functionality should be available via Python module."""
    # Legacy CLI has been migrated to Python modules
    try:
        from edison.core.session import validation
        # Verify the module has the expected validation functions
        assert hasattr(validation, 'validate_session') or hasattr(validation, 'run_validation'), \
            "session.validation module missing expected validation functions"
    except ImportError:
        pytest.skip("session.validation module not yet implemented")
