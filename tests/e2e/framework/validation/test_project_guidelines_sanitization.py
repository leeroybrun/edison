import os
import re
from pathlib import Path

import pytest
from edison.data import get_data_path
from tests.helpers.paths import get_repo_root

# Core guidelines are now in bundled data
CORE_DIR = get_data_path("guidelines")
REPO_ROOT = get_repo_root()


def test_core_guidelines_exist_and_are_project_agnostic():
    # Must exist with required files (current canonical shared guidelines set)
    required = {
        "includes/TDD.md",
        "includes/QUALITY.md",
        "includes/CONTEXT7.md",
        "shared/GIT_WORKFLOW.md",
        "shared/VALIDATION.md",
        "shared/DELEGATION.md",
        "shared/CONTEXT7.md",
        "shared/HONEST_STATUS.md",
    }
    assert CORE_DIR.is_dir(), "Core guidelines directory is missing"
    core_files = {str(p.relative_to(CORE_DIR)) for p in CORE_DIR.rglob("*.md")}
    missing = required - core_files
    assert not missing, f"Missing core guideline files: {sorted(missing)}"

    # Core guidelines must not reference project-specific terms
    forbidden = re.compile(r"\b(next\.js|prisma|uistyles|odoo)\b", re.I)
    offenders = []
    for md in CORE_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            offenders.append(md)
    assert not offenders, f"Core guidelines contain project-specific refs: {offenders}"


@pytest.mark.skip(reason="Project guideline overlays are validated in target projects, not in the Edison framework repo")
def test_project_guidelines_extend_core_and_isolate_project_specifics():
    pass


def test_no_orphaned_guidelines_and_consistent_structure():
    # All core guideline markdowns should have an H1 and a brief intro
    for md in CORE_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore").strip()
        assert text.startswith("# "), f"{md} missing top-level heading"
        assert len(text.splitlines()) > 2, f"{md} should have some content"

    # Project overlays are validated in target projects; this framework repo test
    # intentionally avoids asserting anything about `.edison/guidelines/*`.

