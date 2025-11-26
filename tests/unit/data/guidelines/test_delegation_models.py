"""Delegation guidelines must enumerate decision models and prompts.

This test enforces presence of the orchestrator delegation model definitions so
implementers have a stable source of truth. It intentionally performs literal
string checks (no mocks) to keep verification deterministic.
"""
from __future__ import annotations

from pathlib import Path


GUIDELINE_PATH = Path("src/edison/data/guidelines/orchestrators/DELEGATION.md")


def test_delegation_doc_lists_criteria_and_agent_selection_guidance() -> None:
    """Delegation doc should state what to delegate and how to pick agents."""
    content = GUIDELINE_PATH.read_text()

    for marker in (
        "Delegation Criteria",  # what can be delegated vs direct
        "Tasks to Delegate",  # explicit delegate bucket
        "Tasks to Handle Directly",  # explicit direct bucket
        "Agent Selection Guidance",  # how to choose agents
        "Selection Signals",  # practical cues
    ):
        assert marker in content, f"Missing delegation decision marker: {marker}"


def test_delegation_doc_includes_prompt_and_verification_sections() -> None:
    """Delegation doc should define prompt structure and verification steps."""
    content = GUIDELINE_PATH.read_text()

    for marker in (
        "Delegation Prompt Structure",  # prompt template section
        "Prompt Template",  # actual template label
        "Verification Protocol",  # how to verify delegated work
        "When to Re-delegate",  # when to re-delegate vs fix yourself
        "Parallel vs Sequential",  # delegation patterns
    ):
        assert marker in content, f"Missing delegation execution marker: {marker}"
