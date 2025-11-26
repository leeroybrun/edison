"""
T-062: Ensure code reviewer documentation forbids delegation.
"""
from pathlib import Path


DOC_PATH = Path("src/edison/data/agents/code-reviewer.md")


def test_code_reviewer_doc_explains_no_delegation() -> None:
    content = DOC_PATH.read_text(encoding="utf-8")

    assert "## Why Code Review Cannot Be Delegated" in content
    assert "Never delegate to sub-agents" in content, "No-delegation rule must be explicit in code reviewer doc"
