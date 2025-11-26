from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_claude_md_includes_error_recovery_playbook() -> None:
    """CLAUDE.md must guide assistants through common recovery scenarios."""
    claude_md = REPO_ROOT / "CLAUDE.md"
    assert claude_md.exists(), "CLAUDE.md must exist for assistants"

    content = claude_md.read_text(encoding="utf-8").lower()

    assert "## error recovery" in content, "Add an 'Error Recovery' section header"

    scenarios = [
        "test failure",
        "build failure",
        "validation rejection",
        "circular dependenc",
        "missing file",
    ]
    matched = [scenario for scenario in scenarios if scenario in content]
    assert len(matched) >= 5, "Document at least five recovery scenarios"

    escalation_keywords = ["human help", "escalate", "ask for help"]
    assert any(keyword in content for keyword in escalation_keywords), "Provide guidance on when to escalate to humans"
