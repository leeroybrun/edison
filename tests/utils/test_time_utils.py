from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml


def _write_time_config(repo_root: Path) -> None:
    cfg = {
        "time": {
            "iso8601": {
                "timespec": "seconds",
                "use_z_suffix": True,
                "strip_microseconds": True,
            }
        },
        "subprocess_timeouts": {
            "default": 5.0,
            "git_operations": 5.0,
            "file_operations": 5.0,
        },
    }
    cfg_dir = repo_root / ".edison" / "core" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.joinpath("defaults.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")


@pytest.fixture()
def time_module(isolated_project_env: Path):
    _write_time_config(isolated_project_env)
    import edison.core.utils.time as t  # type: ignore

    importlib.reload(t)
    return t


def test_utc_now_returns_timezone_aware(time_module):
    now = time_module.utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc
    assert now.microsecond == 0


def test_utc_timestamp_format(time_module):
    ts = time_module.utc_timestamp()
    assert ts.endswith("Z")
    # Should parse back into same second
    parsed = time_module.parse_iso8601(ts)
    assert parsed.tzinfo == timezone.utc
    assert parsed.microsecond == 0


def test_parse_iso8601_accepts_offset(time_module):
    dt = time_module.parse_iso8601("2030-01-01T12:00:00+00:00")
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 12
