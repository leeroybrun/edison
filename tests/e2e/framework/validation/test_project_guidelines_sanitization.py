import os
import re
from pathlib import Path

from edison.data import get_data_path
from tests.helpers.paths import get_repo_root

# Core guidelines are now in bundled data
CORE_DIR = get_data_path("guidelines")
REPO_ROOT = get_repo_root()
PROJECT_DIR = REPO_ROOT / ".agents/guidelines"


def test_core_guidelines_exist_and_are_project_agnostic():
    # Must exist with required files
    required = {
        "coding-standards.md",
        "tdd-workflow.md",
        "git-workflow.md",
        "error-handling.md",
        "testing-patterns.md",
    }
    assert CORE_DIR.is_dir(), "Core guidelines directory is missing"
    core_files = {p.name for p in CORE_DIR.glob("*.md")}
    missing = required - core_files
    assert not missing, f"Missing core guideline files: {sorted(missing)}"

    # Core guidelines must not reference project-specific terms
    forbidden = re.compile(r"\b(project|next\.js|prisma|uistyles)\b", re.I)
    offenders = []
    for md in CORE_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            offenders.append(md)
    assert not offenders, f"Core guidelines contain project-specific refs: {offenders}"


def test_project_guidelines_extend_core_and_isolate_project_specifics():
    # Project guidelines directory should exist
    assert PROJECT_DIR.is_dir(), "Project guidelines directory is missing"

    # Project coding standards should include/extend core and include an overlay
    proj_coding = PROJECT_DIR / "coding-standards.md"
    assert proj_coding.is_file(), "Project coding-standards.md missing"

    text = proj_coding.read_text(encoding="utf-8", errors="ignore")
    # Check if references bundled data guidelines (shared directory exists in bundled data)
    assert "{{include:" in text or "edison/data/guidelines" in text or \
           "guidelines/shared" in text, \
           "Project coding standards must reference Edison core guidelines"

    overlays = PROJECT_DIR / "overlays"
    assert overlays.is_dir(), "Project overlays directory missing"
    overlay_file = overlays / "project-coding-standards.md"
    assert overlay_file.is_file(), "project coding standards overlay missing"

    # project-specific tech terms should appear in overlay, not core
    overlay_text = overlay_file.read_text(encoding="utf-8", errors="ignore")
    assert re.search(r"next\.js|prisma|uistyles", overlay_text, re.I), (
        "Expected project-specific terms in overlay"
    )


def test_no_orphaned_guidelines_and_consistent_structure():
    # All core guideline markdowns should have an H1 and a brief intro
    for md in CORE_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore").strip()
        assert text.startswith("# "), f"{md} missing top-level heading"
        assert len(text.splitlines()) > 2, f"{md} should have some content"

    # Project files should either include core or be overlays
    for md in PROJECT_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        assert (
            "{{include:" in text
            or "edison/data/guidelines" in text
            or "guidelines/" in text
            or md.parent.name == "overlays"
        ), f"{md} should include/extend core or be an overlay"

