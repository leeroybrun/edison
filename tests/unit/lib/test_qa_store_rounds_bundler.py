from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest


def _reset_project_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(root))
    import edison.core.paths.resolver as resolver  # type: ignore

    # Clear cached root so PathResolver re-evaluates after env change
    resolver._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]


def test_score_history_jsonl_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_project_root(monkeypatch, tmp_path)
    from edison.core.qa import store

    path = store.score_history_file("sess-1")
    store.append_jsonl(path, {"k": 1})
    store.append_jsonl(path, {"k": 2})

    values = [row["k"] for row in store.read_jsonl(path)]
    assert values == [1, 2]
    assert path.parent == tmp_path / ".project" / "qa" / "score-history"


def test_rounds_next_round_detects_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_project_root(monkeypatch, tmp_path)
    from edison.core.qa import rounds

    ev_root = tmp_path / ".project" / "qa" / "validation-evidence" / "t-1"
    (ev_root / "round-1").mkdir(parents=True)

    assert rounds.latest_round("t-1") == 1
    assert rounds.next_round("t-1") == 2
    assert rounds.round_dir("t-1", 2) == ev_root / "round-2"


def test_bundler_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_project_root(monkeypatch, tmp_path)
    from edison.core.qa import bundler

    cfg: Dict[str, object] = {
        "validation": {
            "artifactPaths": {
                "bundleSummaryFile": "bundle-approved.json",
            }
        }
    }

    path = bundler.bundle_summary_path("t-2", 1, config=cfg)
    assert path == tmp_path / ".project" / "qa" / "validation-evidence" / "t-2" / "round-1" / "bundle-approved.json"

    data = {"approved": True, "round": 1}
    bundler.write_bundle_summary("t-2", 1, data, config=cfg)

    loaded = bundler.load_bundle_summary("t-2", 1, config=cfg)
    assert loaded == data

