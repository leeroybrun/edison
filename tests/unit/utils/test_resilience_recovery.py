
import json
from pathlib import Path

import pytest

from edison.core.utils.resilience import resume_from_recovery

def test_resume_from_recovery_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resume_from_recovery moves session to semantic `active` (dir maps to wip) and updates JSON."""
    from tests.helpers.env_setup import setup_project_root

    setup_project_root(monkeypatch, tmp_path)

    sessions_root = tmp_path / ".project" / "sessions"
    recovery_root = sessions_root / "recovery"
    wip_root = sessions_root / "wip"

    sid = "test-session-123"
    rec_dir = recovery_root / sid
    rec_dir.mkdir(parents=True, exist_ok=True)

    sess_json = rec_dir / "session.json"
    initial_data = {
        "id": sid,
        "state": "recovery",
        "meta": {
            "sessionId": sid,
            "createdAt": "2025-11-22T00:00:00Z",
            "lastActive": "2025-11-22T00:05:00Z",
            "status": "recovery",
        },
        "foo": "bar",
    }
    sess_json.write_text(json.dumps(initial_data, indent=2) + "\n", encoding="utf-8")

    active_dir = resume_from_recovery(rec_dir)

    assert not rec_dir.exists()
    assert active_dir.exists()
    assert active_dir == wip_root / sid

    final_json = active_dir / "session.json"
    data = json.loads(final_json.read_text(encoding="utf-8"))
    assert data["state"] == "active"
    assert data["foo"] == "bar"
