"""
Validation guidelines must document the batched parallel execution model and
the rejection cycle so implementers have an authoritative source of truth.
"""
from __future__ import annotations

from pathlib import Path


GUIDELINE_PATH = Path("src/edison/data/guidelines/shared/VALIDATION.md")


def test_validation_doc_includes_batched_parallel_execution_model():
    """Ensure the batched parallel execution model and consensus rules are documented."""
    content = GUIDELINE_PATH.read_text()

    # Wave diagram anchors
    for label in (
        "Batched Parallel Execution Model",
        "Wave 1: Global Validators",
        "Wave 2: Critical Validators",
        "Wave 3: Comprehensive Validators",
    ):
        assert label in content, f"Missing wave diagram element: {label}"

    # Consensus rules for the global validators
    for rule in (
        "Both global-codex and global-claude must agree",
        "If they disagree, escalate to human review",
        "Tie-breaker: More specific feedback wins",
    ):
        assert rule in content, f"Missing consensus rule: {rule}"


def test_validation_doc_describes_round_rejection_cycle_and_limits():
    """Ensure rejection handling and maximum round limits are captured."""
    content = GUIDELINE_PATH.read_text()

    # Round-based rejection flow
    for marker in (
        "Round N Rejection Cycle",
        "Round 1: Initial Validation",
        'Task returns to {{fn:semantic_state("task","wip")}}',
        "Round 2: Re-validation",
    ):
        assert marker in content, f"Missing rejection cycle element: {marker}"

    # Maximum rounds configuration reference
    assert "validation.maxRounds" in content, "Missing maximum rounds config reference"
    assert "default: {{config.validation.maxRounds}}" in content, "Missing default max rounds template value"
