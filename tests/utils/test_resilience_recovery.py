
import json
from pathlib import Path
import pytest
from edison.core.utils.resilience import resume_from_recovery

def test_resume_from_recovery_integration(tmp_path):
    """Verify resume_from_recovery moves directory and updates JSON."""
    sessions_root = tmp_path / "sessions"
    recovery_root = sessions_root / "recovery"
    active_root = sessions_root / "active"
    
    sid = "test-session-123"
    rec_dir = recovery_root / sid
    rec_dir.mkdir(parents=True)
    
    sess_json = rec_dir / "session.json"
    initial_data = {"id": sid, "state": "Recovery", "foo": "bar"}
    sess_json.write_text(json.dumps(initial_data), encoding="utf-8")
    
    # Run recovery
    active_dir = resume_from_recovery(rec_dir)
    
    # Verify moved
    assert not rec_dir.exists()
    assert active_dir.exists()
    assert active_dir == active_root / sid
    
    # Verify JSON updated
    final_json = active_dir / "session.json"
    assert final_json.exists()
    data = json.loads(final_json.read_text(encoding="utf-8"))
    assert data["state"] == "Active"
    assert data["foo"] == "bar"
