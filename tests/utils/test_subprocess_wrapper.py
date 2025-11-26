from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


# Late import so tests can control configuration files per isolated repo

def _write_timeout_config(root: Path, default: float = 0.2, file_ops: float = 1.0) -> None:
    config_dir = root / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_dir.joinpath("defaults.yaml").write_text(
        "\n".join(
            [
                "project:",
                "  name: subprocess-wrapper-test",
                "subprocess_timeouts:",
                f"  default: {default}",
                f"  file_operations: {file_ops}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    project_cfg_dir = root / ".agents" / "config"
    project_cfg_dir.mkdir(parents=True, exist_ok=True)
    project_cfg_dir.joinpath("project.yml").write_text(
        "project: { name: subprocess-wrapper-test }\n", encoding="utf-8"
    )

    # Ensure cached timeouts are refreshed for each test case
    from edison.core.utils.subprocess import reset_subprocess_timeout_cache 
    reset_subprocess_timeout_cache()


def test_run_with_timeout_honors_configured_value(isolated_project_env: Path) -> None:
    from edison.core.utils.subprocess import run_with_timeout

    _write_timeout_config(isolated_project_env, default=1.0, file_ops=0.5)

    # Should complete within the configured 0.5s window
    result = run_with_timeout(
        [sys.executable, "-c", "import time; time.sleep(0.1)"]
    )

    assert result.returncode == 0


def test_run_with_timeout_raises_on_expiry(isolated_project_env: Path) -> None:
    from edison.core.utils.subprocess import run_with_timeout

    _write_timeout_config(isolated_project_env, default=0.1, file_ops=0.15)

    with pytest.raises(subprocess.TimeoutExpired):
        run_with_timeout(
            [sys.executable, "-c", "import time; time.sleep(0.3)"]
        )


def test_run_with_timeout_respects_timeout_type(isolated_project_env: Path) -> None:
    from edison.core.utils.subprocess import run_with_timeout

    _write_timeout_config(isolated_project_env, default=0.5, file_ops=0.05)

    # Using timeout_type ensures it pulls the correct bucket instead of default
    with pytest.raises(subprocess.TimeoutExpired):
        run_with_timeout(
            [sys.executable, "-c", "import time; time.sleep(0.2)"],
            timeout_type="file_operations",
        )
