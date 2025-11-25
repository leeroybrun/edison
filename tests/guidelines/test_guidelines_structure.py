from __future__ import annotations

from pathlib import Path
import re


# Repo root from this file: guidelines/ → tests/ → core/ → .edison/ → <repo>
REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_GUIDELINES = REPO_ROOT / ".edison/core/guidelines"
CORE_EXTENDED = REPO_ROOT / ".edison/core/guides/extended"
CORE_REFERENCE = REPO_ROOT / ".edison/core/guides/reference"


def _read_head(path: Path, lines: int = 12) -> str:
    text = path.read_text(encoding="utf-8")
    return "\n".join(text.splitlines()[:lines])


def test_core_guideline_filenames_unique_case_insensitive() -> None:
    """
    FINDING-0XY: Duplicate filenames with different cases (e.g. GIT_WORKFLOW.md vs git-workflow.md)

    Guardrail: within `.edison/core/guidelines/` there must be at most one
    guideline per case-insensitive filename.
    """
    assert CORE_GUIDELINES.is_dir()

    files = [
        f.name
        for f in CORE_GUIDELINES.glob("*.md")
        if f.name.lower() != "readme.md"
    ]

    lower_to_name: dict[str, str] = {}
    duplicates: list[str] = []

    for name in sorted(files):
        key = name.lower()
        existing = lower_to_name.get(key)
        if existing is not None:
            duplicates.append(f"{name} conflicts with {existing}")
        else:
            lower_to_name[key] = name

    assert not duplicates, (
        "Found duplicate guideline filenames (case-insensitive); "
        "consolidate these into a single canonical file: "
        f"{duplicates}"
    )


def test_core_guidelines_and_extended_guides_have_strict_cross_links() -> None:
    """
    FINDING-0XY: Unclear contract between condensed vs extended guides.

    Contract:
    - For every topic that exists in both `core/guidelines` and
      `core/guides/extended` (same basename), the *guideline* must contain
      a top-of-file link:
        '> **Extended Version**: See [core/guides/extended/X.md](../../guides/extended/X.md) ...'
    - The *extended* guide must contain a top-of-file link:
        '> **Condensed Summary**: See [core/guidelines/X.md](../../guidelines/X.md) ...'

    We enforce the presence of these exact paths near the top of each file
    so agents can rely on a predictable cross-link convention.
    """
    assert CORE_GUIDELINES.is_dir()
    assert CORE_EXTENDED.is_dir()

    guidelines = {
        f.name: f
        for f in CORE_GUIDELINES.glob("*.md")
        if f.name.lower() != "readme.md"
    }
    extended = {f.name: f for f in CORE_EXTENDED.glob("*.md")}

    issues: list[str] = []

    for name, g_path in sorted(guidelines.items()):
        e_path = extended.get(name)
        if e_path is None:
            # Not every guideline has an extended guide (e.g. resilience),
            # only enforce the contract where both exist.
            continue

        g_head = _read_head(g_path)
        e_head = _read_head(e_path)

        expected_ext_path = f"../../guides/extended/{name}"
        expected_guideline_path = f"../../guidelines/{name}"

        if "Extended Version" not in g_head or expected_ext_path not in g_head:
            issues.append(
                f"Guideline {name} is missing canonical extended cross-link "
                f"(expected 'Extended Version' with path {expected_ext_path!r} "
                "near the top of the file)."
            )

        if "Condensed Summary" not in e_head or expected_guideline_path not in e_head:
            issues.append(
                f"Extended guide {name} is missing canonical condensed cross-link "
                f"(expected 'Condensed Summary' with path {expected_guideline_path!r} "
                "near the top of the file)."
            )

    assert not issues, "Cross-link contract violations:\n" + "\n".join(issues)


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


def test_reference_guides_do_not_point_to_missing_markdown_files() -> None:
    """
    Reference guides must not point to non-existent .md files.

    We treat backticked paths and markdown links that end in `.md` as internal
    repository references and assert that the corresponding files exist.
    Placeholder patterns containing `{}` braces are ignored.
    """
    assert CORE_REFERENCE.is_dir()

    missing: list[str] = []

    for ref_path in sorted(CORE_REFERENCE.glob("*.md")):
        content = ref_path.read_text(encoding="utf-8")
        for rel in _extract_markdown_paths(content):
            # Skip placeholders like `.project/sessions/{wip,done,validated}/SESSION-ID.md`
            if "{" in rel or "}" in rel:
                continue
            # Only enforce for repo-relative paths (no scheme like http://)
            if "://" in rel:
                continue

            target = (REPO_ROOT / rel).resolve()
            try:
                target.relative_to(REPO_ROOT)
            except ValueError:
                # Outside repo; treat as out-of-scope.
                continue

            if not target.exists():
                missing.append(f"{ref_path.relative_to(REPO_ROOT)} -> {rel}")

    assert not missing, (
        "Reference guides contain links to missing .md files; "
        "update paths to match current guideline locations:\n"
        + "\n".join(missing)
    )


DUPLICATED_TOPICS = [
    "CONTEXT7",
    "DELEGATION",
    "EPHEMERAL_SUMMARIES_POLICY",
    "GIT_WORKFLOW",
    "HONEST_STATUS",
    "QUALITY",
    "SESSION_WORKFLOW",
    "TDD",
    "VALIDATION",
]


def test_condensed_and_extended_have_explicit_path_cross_links() -> None:
    """
    Phase 3A: Condensed vs extended guideline pairs must expose explicit
    path cross-links for use by higher-level composition and QA tooling.

    Contract (for duplicated topics only):
      - Guideline includes:  'See extended guide: .edison/core/guides/extended/X.md'
      - Extended includes:   'Condensed version: .edison/core/guidelines/X.md'
    """
    issues: list[str] = []

    for name in DUPLICATED_TOPICS:
        guideline = CORE_GUIDELINES / f"{name}.md"
        extended = CORE_EXTENDED / f"{name}.md"

        assert guideline.is_file(), f"Missing core guideline for topic {name}"
        assert extended.is_file(), f"Missing extended guide for topic {name}"

        g_text = guideline.read_text(encoding="utf-8")
        e_text = extended.read_text(encoding="utf-8")

        forward = f"See extended guide: .edison/core/guides/extended/{name}.md"
        reverse = f"Condensed version: .edison/core/guidelines/{name}.md"

        if forward not in g_text:
            issues.append(
                f"{guideline.relative_to(REPO_ROOT)} missing explicit forward cross-link "
                f"({forward!r})."
            )
        if reverse not in e_text:
            issues.append(
                f"{extended.relative_to(REPO_ROOT)} missing explicit reverse cross-link "
                f"({reverse!r})."
            )

    assert not issues, "Explicit guideline cross-link violations:\n" + "\n".join(issues)

