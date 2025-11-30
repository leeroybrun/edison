from __future__ import annotations

from pathlib import Path

from edison.core.config.domains.timeouts import TimeoutsConfig


def test_subprocess_timeouts_use_timeouts_config(isolated_project_env: Path) -> None:
    """Test that subprocess operations use TimeoutsConfig for timeout values.

    The old subprocess_timeouts section has been migrated to the timeouts section
    with standardized _seconds suffix naming convention.
    """
    cfg = TimeoutsConfig(repo_root=isolated_project_env)

    # Verify the standard timeout values are accessible
    assert cfg.git_operations_seconds == 60.0
    assert cfg.db_operations_seconds == 30.0
    assert cfg.test_execution_seconds == 300.0
    assert cfg.build_operations_seconds == 600.0
    assert cfg.default_seconds == 60.0
