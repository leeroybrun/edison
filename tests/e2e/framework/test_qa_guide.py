import os
import re
from pathlib import Path


GUIDE_PATH = Path(".edison/core/docs/guides/qa.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _triple_backticks_balanced(text: str) -> bool:
    return text.count("```") % 2 == 0


def _relative_md_links(text: str):
    import re as _re
    links = _re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    rel = []
    for href in links:
        if href.startswith("http") or href.startswith("#"):
            continue
        if "://" in href:
            continue
        href = href.split("#")[0]
        if href.strip():
            rel.append(href)
    return rel


def test_qa_guide_exists_and_long_enough():
    assert GUIDE_PATH.exists(), "qa.md guide must exist at .edison/core/docs/guides/qa.md"
    content = _read(GUIDE_PATH)
    line_count = len(content.splitlines())
    assert line_count >= 400, f"qa.md too short: {line_count} lines (expected >= 400)"


def test_qa_guide_has_required_sections():
    content = _read(GUIDE_PATH)
    required_sections = [
        "QA Philosophy",
        "Validation Workflow",
        "TDD Validation",
        "Validator Templates",
        "Validation Dimensions",
        "Evidence Requirements",
        "Context7 Usage",
        "Approval Criteria",
        "Rejection Handling",
        "Validator Role",
        "Common Validation Scenarios",
        "Troubleshooting",
    ]
    missing = [s for s in required_sections if s not in content]
    assert not missing, f"qa.md missing sections: {missing}"


def test_qa_guide_describes_fail_closed_evidence_tdd():
    content = _read(GUIDE_PATH)
    assert "fail-closed" in content.lower() or "fail closed" in content.lower()
    assert "evidence" in content.lower()
    for term in ["RED", "GREEN", "REFACTOR"]:
        assert term in content, f"qa.md must verify TDD phase: {term}"


def test_qa_guide_templates_and_dimensions_referenced():
    content = _read(GUIDE_PATH)
    # Must reference validator templates and overlays
    assert ".edison/core/validators/templates" in content
    assert ".agents/validators/overlays" in content
    # Must mention scoring/thresholds by dimension names
    expected_dims = [
        "Architecture", "Code Quality", "Testing", "TDD", "Documentation",
        "Error Handling", "Performance", "Security"
    ]
    for dim in expected_dims:
        assert dim in content, f"qa.md missing validation dimension: {dim}"


def test_qa_guide_is_project_agnostic_and_uses_placeholders():
    content = _read(GUIDE_PATH)
    project_name = os.environ.get("PROJECT_NAME", "").strip() or "example-project"
    extra_terms = [
        t.strip() for t in os.environ.get("PROJECT_TERMS", "").split(",") if t.strip()
    ]
    forbidden = [re.escape(project_name), *map(re.escape, extra_terms)]
    for pat in forbidden:
        assert not re.search(pat, content, re.IGNORECASE), (
            f"qa.md must be project-agnostic; found forbidden pattern: {pat}"
        )
    assert "{PROJECT_NAME}" in content, "qa.md should use {PROJECT_NAME} placeholder"
    assert _triple_backticks_balanced(content), "Unbalanced code fences in qa.md"


def test_qa_guide_links_resolve_on_disk():
    content = _read(GUIDE_PATH)
    md_links = [p for p in _relative_md_links(content) if p.endswith('.md')]
    missing = [p for p in md_links if not Path(p).exists()]
    assert not missing, f"qa.md contains broken markdown links: {missing}"
