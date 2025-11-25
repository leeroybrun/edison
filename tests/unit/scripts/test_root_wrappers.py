from __future__ import annotations

from pathlib import Path


LEGACY_WRAPPERS = {
    "scripts/session_verify.py",
}


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if parent.name == ".edison":
            continue
        if (parent / ".git").exists():
            return parent
    raise AssertionError("repository root not found from tests")


def test_legacy_wrappers_removed() -> None:
    repo = _repo_root()

    for wrapper_rel in LEGACY_WRAPPERS:
        wrapper_path = repo / wrapper_rel
        assert not wrapper_path.exists(), f"Legacy wrapper should be removed: {wrapper_rel}"
