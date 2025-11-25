from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Resolve outer project root (the directory that contains .edison/core/lib)."""
    cur = Path(__file__).resolve()
    for cand in cur.parents:
        if (cand / ".edison" / "core" / "lib" / "config.py").exists():
            return cand
    raise AssertionError("cannot locate Edison project root for archive tests")


def test_dependency_analysis_json_moved_to_architecture_docs() -> None:
    """
    core/lib/dependency_analysis.json must live under docs/architecture as a historical artifact.
    """
    root = _repo_root()
    old_path = root / ".edison" / "core" / "lib" / "dependency_analysis.json"
    new_path = (
        root
        / ".edison"
        / "core"
        / "docs"
        / "architecture"
        / "dependency-analysis-historical.json"
    )

    # Old location must not exist to avoid confusion at runtime.
    assert not old_path.exists(), f"Legacy dependency_analysis.json still present at {old_path}"

    # New archived location must exist for historical reference.
    assert new_path.is_file(), f"Archived dependency analysis missing at {new_path}"


def test_legacy_pathlib_module_not_present_in_core_lib() -> None:
    """
    Legacy core/lib/pathlib.py must not exist after Phase 1 migration.
    """
    root = _repo_root()
    legacy_path = root / ".edison" / "core" / "lib" / "pathlib.py"
    assert not legacy_path.exists(), f"Legacy pathlib module unexpectedly present at {legacy_path}"
