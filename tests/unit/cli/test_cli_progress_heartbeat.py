from __future__ import annotations

import re
import sys
import time

import pytest

from edison.cli._progress import CliProgressConfig, cli_progress

pytestmark = pytest.mark.fast


def _heartbeats(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if "still running" in line]


def _parse_next_update_seconds(line: str) -> float:
    m = re.search(r"next update in ([0-9]+)(ms|s)", line)
    assert m is not None, f"missing next-update hint in: {line!r}"
    value = int(m.group(1))
    unit = m.group(2)
    if unit == "ms":
        return value / 1000.0
    return float(value)


def test_cli_progress_emits_compact_heartbeat_after_threshold(capsys) -> None:
    cfg = CliProgressConfig(
        enabled=True,
        threshold_seconds=0.01,
        interval_seconds=0.02,
        max_interval_seconds=0.05,
        backoff_multiplier=2.0,
        idle_seconds=0.0,
        show_command_once=False,
        show_next_update=True,
    )
    argv = ["evidence", "capture", "007", "--only", "test"]
    with cli_progress(command_name="evidence capture", argv=argv, config=cfg):
        time.sleep(0.08)

    captured = capsys.readouterr()
    assert captured.out == ""

    heartbeats = _heartbeats(captured.err)
    assert heartbeats, f"expected heartbeat lines, got: {captured.err!r}"
    first = heartbeats[0]
    assert "evidence capture" in first
    assert "please wait" in first
    assert "next update in" in first
    assert "--only" not in first
    assert "007" not in first


def test_cli_progress_disabled_is_silent(capsys) -> None:
    cfg = CliProgressConfig(
        enabled=False,
        threshold_seconds=0.0,
        interval_seconds=0.01,
        max_interval_seconds=0.05,
        backoff_multiplier=2.0,
        idle_seconds=0.0,
        show_command_once=False,
        show_next_update=True,
    )
    with cli_progress(command_name="task show", argv=["task", "show", "123"], config=cfg):
        time.sleep(0.03)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_cli_progress_is_idle_heartbeat_suppressed_by_recent_output(capsys) -> None:
    cfg = CliProgressConfig(
        enabled=True,
        threshold_seconds=0.01,
        interval_seconds=0.01,
        max_interval_seconds=0.05,
        backoff_multiplier=2.0,
        idle_seconds=0.2,
        show_command_once=False,
        show_next_update=True,
    )
    with cli_progress(command_name="evidence capture", argv=["evidence", "capture", "007"], config=cfg):
        print("tick", file=sys.stderr, flush=True)
        time.sleep(0.08)

    captured = capsys.readouterr()
    assert _heartbeats(captured.err) == []


def test_cli_progress_backoff_increases_next_update(capsys) -> None:
    cfg = CliProgressConfig(
        enabled=True,
        threshold_seconds=0.01,
        interval_seconds=0.02,
        max_interval_seconds=0.08,
        backoff_multiplier=2.0,
        idle_seconds=0.0,
        show_command_once=False,
        show_next_update=True,
    )
    with cli_progress(command_name="evidence capture", argv=["evidence", "capture", "007"], config=cfg):
        time.sleep(0.18)

    captured = capsys.readouterr()
    heartbeats = _heartbeats(captured.err)
    assert len(heartbeats) >= 2

    next_updates = [_parse_next_update_seconds(line) for line in heartbeats[:3]]
    assert any(b > a for a, b in zip(next_updates, next_updates[1:]))


def test_cli_progress_show_command_once_only_prints_argv_once(capsys) -> None:
    cfg = CliProgressConfig(
        enabled=True,
        threshold_seconds=0.01,
        interval_seconds=0.01,
        max_interval_seconds=0.05,
        backoff_multiplier=2.0,
        idle_seconds=0.0,
        show_command_once=True,
        show_next_update=True,
    )
    argv = ["evidence", "capture", "007", "--only", "test"]
    with cli_progress(command_name="evidence capture", argv=argv, config=cfg):
        time.sleep(0.09)

    captured = capsys.readouterr()
    assert captured.err.count("--only") == 1
