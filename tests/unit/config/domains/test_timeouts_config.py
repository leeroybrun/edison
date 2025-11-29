from __future__ import annotations

import importlib
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from edison.core.config import ConfigManager


def _write_timeouts_config(
    repo_root: Path,
    *,
    git_seconds: float = 0.2,
    db_seconds: float = 0.2,
    lock_seconds: float = 0.2,
) -> Path:
    """Ensure defaults.yaml contains the timeouts section with given values."""
    defaults_path = repo_root / ".edison" / "core" / "config" / "defaults.yaml"
    defaults_path.parent.mkdir(parents=True, exist_ok=True)

    current = yaml.safe_load(defaults_path.read_text()) if defaults_path.exists() else {}
    if current is None:
        current = {}

    current.setdefault("project", {"name": "timeouts-tests"})
    current["timeouts"] = {
        "git_operations_seconds": git_seconds,
        "db_operations_seconds": db_seconds,
        "json_io_lock_seconds": lock_seconds,
    }

    defaults_path.write_text(yaml.safe_dump(current), encoding="utf-8")
    return defaults_path


def test_timeouts_defaults_present_in_config(isolated_project_env: Path) -> None:
    """ConfigManager should expose timeout defaults from defaults.yaml."""
    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    timeouts = cfg.get("timeouts") or {}

    assert timeouts.get("git_operations_seconds") == 60.0
    assert timeouts.get("db_operations_seconds") == 30.0
    assert timeouts.get("json_io_lock_seconds") == 5.0


def test_timeouts_env_overrides_defaults(monkeypatch, isolated_project_env: Path) -> None:
    """Environment variables must override YAML timeout defaults."""
    base_cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    base_timeouts = base_cfg.get("timeouts") or {}

    assert base_timeouts.get("git_operations_seconds") == 60.0
    assert base_timeouts.get("db_operations_seconds") == 30.0
    assert base_timeouts.get("json_io_lock_seconds") == 5.0

    monkeypatch.setenv("EDISON_timeouts__git_operations_seconds", "12.5")
    monkeypatch.setenv("EDISON_timeouts__db_operations_seconds", "45.0")
    monkeypatch.setenv("EDISON_timeouts__json_io_lock_seconds", "7.25")

    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    timeouts = cfg.get("timeouts") or {}

    assert timeouts["git_operations_seconds"] == pytest.approx(12.5)
    assert timeouts["db_operations_seconds"] == pytest.approx(45.0)
    assert timeouts["json_io_lock_seconds"] == pytest.approx(7.25)


def test_run_git_and_db_commands_use_configured_timeouts(monkeypatch, isolated_project_env: Path) -> None:
    """Subprocess wrappers should honor config-driven git/db timeouts (with env overrides)."""
    _write_timeouts_config(isolated_project_env, git_seconds=0.15, db_seconds=0.15)
    monkeypatch.setenv("EDISON_timeouts__git_operations_seconds", "0.1")
    monkeypatch.setenv("EDISON_timeouts__db_operations_seconds", "0.1")

    from edison.core.utils.subprocess import (
        reset_subprocess_timeout_cache,
        run_db_command,
        run_git_command,
    )

    reset_subprocess_timeout_cache()

    with pytest.raises(subprocess.TimeoutExpired):
        run_git_command([sys.executable, "-c", "import time; time.sleep(0.3)"], cwd=isolated_project_env)

    with pytest.raises(subprocess.TimeoutExpired):
        run_db_command([sys.executable, "-c", "import time; time.sleep(0.3)"], cwd=isolated_project_env)


def test_json_io_uses_configured_lock_timeout(monkeypatch, isolated_project_env: Path, tmp_path: Path) -> None:
    """JSON I/O lock acquisition should respect config (and env override via ConfigManager)."""
    _write_timeouts_config(isolated_project_env, lock_seconds=0.05)
    monkeypatch.setenv("EDISON_JSON_IO_LOCK_TIMEOUT", "0.3")  # Legacy env should NOT control behavior
    monkeypatch.setenv("EDISON_timeouts__json_io_lock_seconds", "0.05")

    from edison.core.utils.io import json as json_io
    from edison.core.utils.io import locking as locklib

    importlib.reload(json_io)

    assert json_io._lock_timeout_seconds() == pytest.approx(0.05)

    target = tmp_path / "locked.json"
    target.write_text("{}", encoding="utf-8")

    with locklib.acquire_file_lock(target, timeout=1.0, fail_open=False):
        start = time.time()
        with json_io._lock_context(target, acquire_lock=True):
            pass
        elapsed = time.time() - start

    assert elapsed < 0.25
