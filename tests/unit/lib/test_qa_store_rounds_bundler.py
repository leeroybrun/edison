from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest
from tests.helpers.env_setup import setup_project_root


def test_score_history_jsonl_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
    from edison.core.qa import scoring
    
    # Use the scoring module's public API
    scoring.track_validation_score("sess-1", "test-val", {"k": 1}, 1.0)
    scoring.track_validation_score("sess-1", "test-val", {"k": 2}, 2.0)

    entries = scoring.get_score_history("sess-1")
    assert len(entries) == 2
    # Verify they're ordered by timestamp and contain expected data
    assert entries[0]["scores"]["k"] == 1
    assert entries[1]["scores"]["k"] == 2


@pytest.mark.skip(reason="rounds.py module deleted - use EvidenceService instead")
def test_rounds_next_round_detects_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
    from edison.core.qa import rounds

    ev_root = tmp_path / ".project" / "qa" / "validation-evidence" / "t-1"
    (ev_root / "round-1").mkdir(parents=True)

    assert rounds.latest_round("t-1") == 1
    assert rounds.next_round("t-1") == 2
    assert rounds.round_dir("t-1", 2) == ev_root / "round-2"


def test_bundler_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
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

