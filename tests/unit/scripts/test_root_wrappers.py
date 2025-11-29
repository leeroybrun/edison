from __future__ import annotations

from pathlib import Path

from tests.helpers.paths import get_repo_root


LEGACY_WRAPPERS = {
    "scripts/session_verify.py",
}


def test_legacy_wrappers_removed() -> None:
    repo = get_repo_root()

    for wrapper_rel in LEGACY_WRAPPERS:
        wrapper_path = repo / wrapper_rel
        assert not wrapper_path.exists(), f"Legacy wrapper should be removed: {wrapper_rel}"
