"""Guards against legacy cache directories creeping back into the repo.

This test enforces deletion of historical `.agents/.cache` artifacts and
codifies the expected `.gitignore` entries to keep them out going forward.
"""

from __future__ import annotations

from pathlib import Path


LEGACY_CACHE_PATHS = (".agents/.cache", ".edison/.cache")
GITIGNORE_ENTRIES = tuple(path + "/" for path in LEGACY_CACHE_PATHS)


def test_no_legacy_cache_directories_and_gitignore_rules() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    existing = [path for path in LEGACY_CACHE_PATHS if (repo_root / path).exists()]
    assert not existing, (
        "Legacy cache directories present: " + ", ".join(sorted(existing))
    )

    gitignore_path = repo_root / ".gitignore"
    assert gitignore_path.exists(), ".gitignore file missing"

    gitignore_lines = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in gitignore_lines]
    assert not missing, (
        ".gitignore missing legacy cache entries: " + ", ".join(sorted(missing))
    )
