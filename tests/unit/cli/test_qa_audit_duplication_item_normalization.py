from __future__ import annotations

from pathlib import Path

from edison.cli.qa.audit import _normalize_duplication_item


def test_normalize_duplication_item_accepts_new_shape(tmp_path: Path) -> None:
    repo_root = tmp_path
    item = {
        "a": {"path": "guidelines/shared/COMMON.md", "category": "shared", "pack": None},
        "b": {"path": "guidelines/shared/DELEGATION.md", "category": "shared", "pack": None},
        "similarity": 0.42,
    }
    p1, p2, score = _normalize_duplication_item(item, repo_root)
    assert p1 == "guidelines/shared/COMMON.md"
    assert p2 == "guidelines/shared/DELEGATION.md"
    assert score == 0.42









