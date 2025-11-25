"""QA tests for Edison core guideline content quality.

These tests enforce that core guidelines:
- Do not contain auto-generated filler padding lines
- Have a reasonable amount of meaningful content
- Avoid repeated filler-style multi-line blocks

RED phase: with the current filler-heavy guidelines and generator, these
tests are expected to fail. They become GREEN once filler is removed and
guidelines are regenerated with meaningful content only.
"""
from __future__ import annotations

from pathlib import Path
import re

import pytest


FILLER_PATTERNS = [
    re.compile(
        r"Additional note \d+: adhere to guidelines and validate behavior deterministically\.",
        re.IGNORECASE,
    ),
    re.compile(
        r"filler-block-\d+: keep style and structure consistent",
        re.IGNORECASE,
    ),
]

INCLUDE_PATTERN = re.compile(r"\{\{include:(.+?)\}\}")


def _core_guidelines_dir(repo_root: Path) -> Path:
    return repo_root / ".edison" / "core" / "guidelines"


def _iter_core_guideline_files(repo_root: Path):
    gdir = _core_guidelines_dir(repo_root)
    for path in sorted(gdir.glob("*.md")):
        # README is navigational only; content checks focus on per-topic guides.
        if path.name.lower() == "readme.md":
            continue
        yield path


def _is_filler_line(line: str) -> bool:
    stripped = line.strip().lstrip("-").strip()
    for pat in FILLER_PATTERNS:
        if pat.search(stripped):
            return True
    return False


def _is_meaningful_line(line: str) -> bool:
    """Heuristic: non-empty, non-filler, and reasonably substantive."""
    stripped = line.strip()
    if not stripped:
        return False
    if _is_filler_line(stripped):
        return False
    # Very short lines (e.g. list bullets or headings only) are ignored here.
    return len(stripped) >= 20


def has_meaningful_content(lines: list[str]) -> bool:
    """Return True if a guideline has enough non-filler content.

    We treat a file as meaningful when:
    - It has at least 20 non-empty lines, and
    - At least 20 of those lines are substantive, and
    - Substantive lines are at least 40% of non-empty lines.

    This is tuned so that current filler-heavy generated guidelines fail,
    while shorter hand-written core guidelines still pass.
    """
    non_empty = [ln for ln in lines if ln.strip()]
    if len(non_empty) < 20:
        return False

    meaningful = [ln for ln in non_empty if _is_meaningful_line(ln)]
    if len(meaningful) < 20:
        return False

    ratio = len(meaningful) / len(non_empty)
    return ratio >= 0.4


# Names must stay in sync with scripts/generate_guidelines.py
GENERATED_CORE_GUIDELINES = {
    "architecture.md",
    "code-quality.md",
    "configuration.md",
    "deployment.md",
    "dependencies.md",
    "documentation.md",
    "naming-conventions.md",
    "performance.md",
    "review-process.md",
    "error-handling.md",
    "testing.md",
    "testing-patterns.md",
    "coding-standards.md",
    # Scenario guides
    "error-recovery.md",
    "concurrent-operations.md",
    "data-validation.md",
    "api-design.md",
}


@pytest.mark.qa
@pytest.mark.fast
def test_core_guidelines_have_no_auto_generated_filler(repo_root: Path) -> None:
    """Core guidelines must not contain known filler padding lines."""
    offenders: list[Path] = []
    for path in _iter_core_guideline_files(repo_root):
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(_is_filler_line(ln) for ln in lines):
            offenders.append(path.relative_to(repo_root))

    assert offenders == [], (
        "Core guidelines contain auto-generated filler lines that should be "
        f"removed by scripts/generate_guidelines.py: {offenders}"
    )


@pytest.mark.qa
@pytest.mark.fast
def test_generated_core_guidelines_have_meaningful_content(repo_root: Path) -> None:
    """
    Generated core guidelines should be mostly substantive, not padding.

    We support two shapes of generated guidelines:
    - Full, standalone documents with >=20 substantive lines
    - Thin wrappers that delegate to another guideline via {{include:...}}
      (for example project-specific aliases that point at a shared core guide)
    """
    gdir = _core_guidelines_dir(repo_root)

    missing: list[str] = []
    weak: list[Path] = []

    for filename in sorted(GENERATED_CORE_GUIDELINES):
        path = gdir / filename
        if not path.exists():
            missing.append(filename)
            continue

        text = path.read_text(encoding="utf-8")

        # Allow thin wrapper guidelines that delegate to another canonical guide
        # using the {{include:...}} template, as long as the include target exists.
        include_targets = [
            m.strip() for m in INCLUDE_PATTERN.findall(text) if m.strip()
        ]
        if include_targets:
            unresolved = [
                target
                for target in include_targets
                if not (repo_root / target).exists()
            ]
            if unresolved:
                weak.append(path.relative_to(repo_root))
            continue

        lines = text.splitlines()
        if not (has_meaningful_content(lines) and len(lines) >= 20):
            weak.append(path.relative_to(repo_root))

    assert not missing, f"Expected generated guideline files are missing: {missing}"
    assert not weak, (
        "Generated core guidelines should have meaningful content and at least "
        "20 lines each; the following files violate this expectation: "
        f"{weak}"
    )


@pytest.mark.qa
@pytest.mark.fast
def test_no_duplicate_filler_blocks_within_guidelines(repo_root: Path) -> None:
    """Core guidelines must not repeat canonicalized filler blocks.

    This is intentionally focused on filler-style lines (\"Additional note N...\"
    and \"filler-block-N...\") rather than generally enforcing DRYness for all
    content. The goal is to prevent artificially inflated sections made of
    repeated filler blocks.
    """

    def canonicalize_filler(line: str) -> str:
        # Normalize numbers so that "Additional note 1" and "Additional note 2"
        # look identical for duplication detection.
        stripped = line.strip().lstrip("-").strip()
        stripped = re.sub(r"\d+", "<NUM>", stripped)
        return stripped

    offenders: list[Path] = []

    for path in _iter_core_guideline_files(repo_root):
        lines = path.read_text(encoding="utf-8").splitlines()
        canon_filler_lines = [
            canonicalize_filler(ln) for ln in lines if _is_filler_line(ln)
        ]
        if not canon_filler_lines:
            continue

        # Look for any repeated 3-line canonical filler window within a file.
        seen_blocks: set[tuple[str, ...]] = set()
        duplicate_found = False
        for idx in range(0, len(canon_filler_lines) - 2):
            block = tuple(canon_filler_lines[idx : idx + 3])
            if block in seen_blocks:
                duplicate_found = True
                break
            seen_blocks.add(block)

        if duplicate_found:
            offenders.append(path.relative_to(repo_root))

    assert offenders == [], (
        "Core guidelines contain repeated canonical filler blocks; remove "
        f"these auto-generated sections: {offenders}"
    )
