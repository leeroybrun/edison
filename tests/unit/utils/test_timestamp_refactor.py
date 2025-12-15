import os
import shutil
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import re

from edison.core.config.domains import OrchestratorConfig
from edison.core.session.lifecycle.recovery import handle_timeout
from edison.core.utils.time import utc_timestamp

# Helper to create a valid repo environment
@pytest.fixture
def valid_repo(tmp_path):
    # Create .edison/config.yaml
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    config_path = edison_dir / "config.yaml"
    with open(config_path, "w") as f:
        f.write("""
orchestrators:
  default: test
  profiles:
    test:
      command: echo
""")
    return tmp_path

def test_orchestrator_config_timestamp_format(valid_repo):
    """Test that OrchestratorConfig generates canonical timestamps."""
    config = OrchestratorConfig(repo_root=valid_repo)
    tokens = config._build_tokens({})
    
    ts = tokens["timestamp"]

    # Canonical format check: should end with Z (if configured) and no microseconds
    # Based on our probe, we expect Z.
    assert ts.endswith("Z"), f"Timestamp {ts} should end with Z"
    assert "." not in ts, f"Timestamp {ts} should not have microseconds"
    
    # Strict check against utc_timestamp format (assuming timing allows close match, but we check format)
    # Actually, since we can't control time, we just check the format characteristics
    # identical to what utc_timestamp() produces.
    canonical_example = utc_timestamp()
    if canonical_example.endswith("Z"):
        assert ts.endswith("Z")
    else:
        assert ts.endswith("+00:00")

def test_orchestrator_launcher_log_timestamp(valid_repo):
    """Test that launcher logs use canonical timestamp."""
    # Import locally to avoid circular import at module level
    from edison.core.orchestrator import OrchestratorLauncher

    config = OrchestratorConfig(repo_root=valid_repo)

    if "test" not in config.list_profiles():
        pytest.skip("Test profile 'test' not found in loaded configuration (env config overrides local?)")

    # Dummy session context
    class DummyContext:
        project_root = valid_repo
        session_worktree = valid_repo
        session_id = "test_session"
        session = {"meta": {"id": "test_session"}}

    launcher = OrchestratorLauncher(config, DummyContext())
    
    log_path = valid_repo / "launcher.log"
    
    # Launch simple command
    launcher.launch("test", log_path=log_path)
    
    # Check log content
    content = log_path.read_text()

    # Extract timestamp: [launch] TIMESTAMP profile=test
    match = re.search(r"\[launch\] (.*?) profile=", content)
    assert match, "Could not find timestamp in log"
    ts = match.group(1)
    
    # Canonical checks
    # Currently this uses datetime.now(timezone.utc).isoformat(), which has micros and +00:00
    # So this should FAIL if we enforce Z and no micros
    assert ts.endswith("Z"), f"Log timestamp {ts} should end with Z"
    assert "." not in ts, f"Log timestamp {ts} should not have microseconds"

def test_session_recovery_timestamp(tmp_path, monkeypatch):
    """Test that session recovery uses canonical timestamp."""
    import json
    from edison.core.session.persistence.repository import SessionRepository

    # Use real path resolution (no module patching) by setting the canonical env var.
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    # Ensure a valid session exists in the canonical layout.
    sid = "sess-123"
    repo = SessionRepository(project_root=tmp_path)
    session_dir = repo.ensure_session(sid, state="active")

    rec_dir = handle_timeout(session_dir)
    recovery_json = rec_dir / "recovery.json"
    assert recovery_json.exists()

    data = json.loads(recovery_json.read_text())
    ts = data["captured_at"]
    assert ts.endswith("Z"), f"Recovery timestamp {ts} should end with Z"
