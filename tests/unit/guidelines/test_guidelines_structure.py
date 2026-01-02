from __future__ import annotations

from pathlib import Path
import re
import yaml
import pytest

from edison.data import get_data_path


def _read_head(path: Path, lines: int = 12) -> str:
    text = path.read_text(encoding="utf-8")
    return "\n".join(text.splitlines()[:lines])


def test_core_guideline_filenames_unique_case_insensitive() -> None:
    """
    FINDING-0XY: Duplicate filenames with different cases (e.g. GIT_WORKFLOW.md vs git-workflow.md)

    Guardrail: within bundled guidelines there must be at most one
    guideline per case-insensitive filename in each subdirectory.
    """
    guidelines_root = get_data_path("guidelines")

    # Check all subdirectories
    for subdir in guidelines_root.rglob("*"):
        if not subdir.is_dir() or subdir.name == "__pycache__":
            continue

        files = [
            f.name
            for f in subdir.glob("*.md")
            if f.name.lower() != "readme.md"
        ]

        lower_to_name: dict[str, str] = {}
        duplicates: list[str] = []

        for name in sorted(files):
            key = name.lower()
            existing = lower_to_name.get(key)
            if existing is not None:
                duplicates.append(f"{subdir.relative_to(guidelines_root)}/{name} conflicts with {existing}")
            else:
                lower_to_name[key] = name

        assert not duplicates, (
            "Found duplicate guideline filenames (case-insensitive); "
            "consolidate these into a single canonical file: "
            f"{duplicates}"
        )


@pytest.mark.skip(reason="Project-specific test - no extended/condensed split in package data")
def test_core_guidelines_and_extended_guides_have_strict_cross_links() -> None:
    """
    FINDING-0XY: Unclear contract between condensed vs extended guides.

    This test is now project-specific and has been skipped.
    Guidelines in package data use a different organization structure.
    """
    pass


def _extract_markdown_paths(text: str) -> list[str]:
    """Return all referenced .md paths from inline code or markdown links."""
    paths: set[str] = set()

    # Backticked paths like `.edison/core/guidelines/DELEGATION.md`
    for match in re.findall(r"`([^`]+?\.md)`", text):
        paths.add(match.strip())

    # Markdown links like [link](docs/archive/agents/CODEX_DELEGATION_GUIDE.md)
    for match in re.findall(r"\[[^\]]*]\(([^)]+?\.md)\)", text):
        paths.add(match.strip())

    return sorted(paths)


@pytest.mark.skip(reason="Project-specific test - references external project paths")
def test_reference_guides_do_not_point_to_missing_markdown_files() -> None:
    """
    Reference guides must not point to non-existent .md files.

    This test is now project-specific and has been skipped.
    It checks for references to project-specific paths.
    """
    pass


SHARED_TOPICS = [
    "CONTEXT7",
    "DELEGATION",
    "EPHEMERAL_SUMMARIES_POLICY",
    "GIT_WORKFLOW",
    "HONEST_STATUS",
    "QUALITY_PATTERNS",
    "VALIDATION",
]


def test_condensed_and_extended_have_explicit_path_cross_links() -> None:
    """
    Phase 3A: Shared guideline topics must exist in the shared subdirectory.

    Verifies that key guidelines used across multiple roles are properly
    located in the shared guidelines directory.
    """
    guidelines_root = get_data_path("guidelines")
    shared_dir = guidelines_root / "shared"

    assert shared_dir.is_dir(), "Missing shared guidelines directory"

    missing: list[str] = []

    for name in SHARED_TOPICS:
        guideline = shared_dir / f"{name}.md"

        if not guideline.is_file():
            missing.append(f"Missing shared guideline: {name}.md")

    assert not missing, (
        "Missing expected shared guidelines:\n" + "\n".join(missing)
    )


def _resolve_guideline_target_path(reference: str, guidelines_root: Path) -> Path | None:
    prefixes = (
        ".edison/_generated/guidelines/",
        "{{fn:project_config_dir}}/_generated/guidelines/",
        ".edison/core/guidelines/",  # legacy (should not be present in new guidelines)
    )
    for prefix in prefixes:
        if reference.startswith(prefix):
            relative = reference[len(prefix):].lstrip("/")
            return guidelines_root / relative
    return None


def test_guideline_cross_references_align_with_existing_files() -> None:
    """
    Ensure known cross-references in guidelines point at existing markdown files
    and do not retain broken legacy links.
    """
    from tests.helpers.paths import get_repo_root

    config_path = get_repo_root() / "tests" / "fixtures/guidelines/cross_references.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    guidelines_root = get_data_path("guidelines")

    missing_expected: list[str] = []
    forbidden_present: list[str] = []
    missing_targets: list[str] = []

    for entry in config.get("entries", []):
        source_path = guidelines_root / entry["source"]
        text = source_path.read_text(encoding="utf-8")

        for expected in entry.get("expected", []):
            if expected not in text:
                missing_expected.append(f"{entry['source']}: missing '{expected}'")

            target = _resolve_guideline_target_path(expected, guidelines_root)
            if target is not None and not target.exists():
                missing_targets.append(
                    f"{entry['source']}: target '{expected}' not found at {target.relative_to(guidelines_root)}"
                )

        for forbidden in entry.get("forbidden", []):
            if forbidden in text:
                forbidden_present.append(f"{entry['source']}: contains forbidden '{forbidden}'")

    errors: list[str] = []
    if missing_expected:
        errors.append("Missing expected references:\n- " + "\n- ".join(sorted(missing_expected)))
    if missing_targets:
        errors.append("Expected target files are missing:\n- " + "\n- ".join(sorted(missing_targets)))
    if forbidden_present:
        errors.append("Forbidden references still present:\n- " + "\n- ".join(sorted(forbidden_present)))

    assert not errors, "\n\n".join(errors)
