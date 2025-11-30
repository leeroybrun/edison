import os
import re
from pathlib import Path
import pytest
from edison.data import get_data_path

pytestmark = pytest.mark.skip(reason="Documentation not yet written - guide files moved/pending")

# Guide doesn't exist yet - when added, it will be in bundled data
GUIDE_PATH = get_data_path("docs", "guides/task.md")


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _triple_backticks_balanced(text: str) -> bool:
    return text.count("```") % 2 == 0


def _relative_md_links(text: str):
    # Find markdown links: [label](target)
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    rel = []
    for href in links:
        if href.startswith("http") or href.startswith("#"):
            continue
        if "://" in href:
            continue
        # strip anchors
        href = href.split("#")[0]
        if href.strip():
            rel.append(href)
    return rel


def test_task_guide_exists_and_long_enough():
    assert GUIDE_PATH.exists(), "task.md guide must exist in bundled data (docs/guides/task.md)"
    content = _read_file(GUIDE_PATH)
    line_count = len(content.splitlines())
    assert line_count >= 400, f"task.md too short: {line_count} lines (expected >= 400)"


def test_task_guide_has_required_sections():
    content = _read_file(GUIDE_PATH)
    required_sections = [
        "Task File Structure",
        "Task Lifecycle",
        "Task File Template",
        "TDD Evidence Recording",
        "Acceptance Criteria",
        "Task Dependencies",
        "Multi-Session Tasks",
        "Parallel Task Execution",
        "Task Validation",
        "Common Patterns",
        "Troubleshooting",
    ]
    missing = [s for s in required_sections if s not in content]
    assert not missing, f"task.md missing sections: {missing}"

    # Naming convention mention
    assert "task-{ID}-{slug}.md" in content, "task.md must specify naming convention task-{ID}-{slug}.md"

    # Location compatibility mention
    assert ".project/tasks/active/" in content and ".project/tasks/completed/" in content, (
        "task.md must mention active/completed locations"
    )


def test_task_guide_has_frontmatter_and_template():
    content = _read_file(GUIDE_PATH)
    assert "frontmatter" in content.lower(), "task.md must describe required frontmatter"
    assert "copy-paste template" in content.lower() or "template" in content, (
        "task.md must include a copy-paste template"
    )
    assert _triple_backticks_balanced(content), "Unbalanced code fences in task.md"


def test_task_guide_tdd_recording_and_evidence_paths():
    content = _read_file(GUIDE_PATH)
    for term in ["RED", "GREEN", "REFACTOR"]:
        assert term in content, f"task.md must describe TDD phase: {term}"
    assert ".project/qa/validation-evidence" in content, (
        "task.md must mention evidence path under .project/qa/validation-evidence"
    )


def test_task_guide_is_project_agnostic():
    content = _read_file(GUIDE_PATH)
    project_name = os.environ.get("PROJECT_NAME", "").strip() or "example-project"
    extra_terms = [
        t.strip() for t in os.environ.get("PROJECT_TERMS", "").split(",") if t.strip()
    ]
    forbidden = [re.escape(project_name), *map(re.escape, extra_terms)]
    for pat in forbidden:
        assert not re.search(pat, content, re.IGNORECASE), (
            f"task.md must be project-agnostic; found forbidden pattern: {pat}"
        )
    assert "{PROJECT_NAME}" in content, "task.md should use {PROJECT_NAME} placeholder"


def test_task_guide_links_resolve_on_disk():
    content = _read_file(GUIDE_PATH)
    md_links = [p for p in _relative_md_links(content) if p.endswith('.md')]
    missing = [p for p in md_links if not Path(p).exists()]
    assert not missing, f"task.md contains broken markdown links: {missing}"
