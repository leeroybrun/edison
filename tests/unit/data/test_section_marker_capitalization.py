"""T-XXX: Enforce lowercase section/extend markers in markdown sources.

Edison composition markers are case-insensitive, but we standardize on lowercase
for consistency across core + packs.
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers.paths import get_repo_root


ROOT = get_repo_root()
DATA_DIR = ROOT / "src" / "edison" / "data"


def _iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    files.extend(root.rglob("*.md"))
    files.extend(root.rglob("*.mdc"))
    return files


def test_section_and_extend_markers_are_lowercase() -> None:
    md_files = _iter_markdown_files(DATA_DIR)
    assert md_files, "No markdown sources found under src/edison/data"

    # We standardize markers, even though parsing is case-insensitive.
    forbidden = [
        "<!-- SECTION:",
        "<!-- /SECTION:",
        "<!-- EXTEND:",
        "<!-- /EXTEND",
    ]

    violations: list[tuple[str, int, str]] = []
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        for idx, line in enumerate(text.splitlines(), start=1):
            if any(tok in line for tok in forbidden):
                violations.append((str(path.relative_to(ROOT)), idx, line.strip()))

    assert not violations, (
        "Found non-standard (uppercase) section markers. Use lowercase:\n"
        "- <!-- section: name --> ... <!-- /section: name -->\n"
        "- <!-- extend: name --> ... <!-- /extend -->\n\n"
        + "\n".join(f"{p}:{ln}: {content}" for p, ln, content in violations[:50])
        + ("\n... (more)" if len(violations) > 50 else "")
    )





