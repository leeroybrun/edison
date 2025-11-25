from __future__ import annotations

from pathlib import Path
import re


# Repo root from this file: guidelines/ → tests/ → core/ → .edison/ → <repo>
REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_GUIDELINES = REPO_ROOT / ".edison/core/guidelines"
CORE_EXTENDED = REPO_ROOT / ".edison/core/guides/extended"


FILLER_PATTERNS = [
    re.compile(r"Additional note \d+:", re.IGNORECASE),
    re.compile(r"Note \d+:", re.IGNORECASE),
]


def _iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for root in (CORE_GUIDELINES, CORE_EXTENDED):
        assert root.is_dir()
        files.extend(sorted(root.glob("*.md")))
    return files


def test_guidelines_have_no_additional_note_filler() -> None:
    """
    FINDING-0XY.1.5: Remove filler lines like 'Additional note N: ...'

    Guardrail: any future re-introduction of generator-style padding lines
    must immediately fail tests.
    """
    offenders: list[str] = []

    for path in _iter_markdown_files():
        content = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if any(p.search(stripped) for p in FILLER_PATTERNS):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno} - {stripped}")

    assert not offenders, (
        "Found filler-style lines in core guidelines/guides; remove generator padding:\n"
        + "\n".join(offenders)
    )


def test_known_misplaced_topics_do_not_exist_anymore() -> None:
    """
    FINDING-0XY.1.5: Known misplaced topics must be removed from core.

    Historically, the audit identified lowercased core guideline variants
    (e.g. git-workflow.md, tdd-workflow.md) that conflicted with canonical
    uppercase versions and project overlays.

    This test ensures those accidental files are not reintroduced.
    """
    deprecated_paths = [
        REPO_ROOT / ".edison/core/guidelines/git-workflow.md",
        REPO_ROOT / ".edison/core/guidelines/tdd-workflow.md",
        REPO_ROOT / ".agents/guidelines/SESSION_WORKFLOW.md",
    ]

    resurrected = [str(p.relative_to(REPO_ROOT)) for p in deprecated_paths if p.exists()]

    assert not resurrected, (
        "Deprecated guideline locations were resurrected; move content into the "
        "canonical core/pack/project layers instead: "
        f"{resurrected}"
    )

