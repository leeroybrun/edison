from __future__ import annotations

from pathlib import Path

from edison.core.config import ConfigManager


def test_subprocess_timeouts_defaults_present(isolated_project_env: Path) -> None:
    """Test that subprocess timeouts are configured with correct defaults."""
    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    timeouts = cfg.get("subprocess_timeouts") or {}

    assert timeouts.get("git_operations") == 30
    assert timeouts.get("test_execution") == 300
    assert timeouts.get("build_operations") == 600
    assert timeouts.get("ai_calls") == 120
    assert timeouts.get("file_operations") == 10
    assert timeouts.get("default") == 60
