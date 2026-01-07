from __future__ import annotations

import time

from edison.cli._progress import CliProgressConfig, cli_progress


def test_cli_progress_emits_to_stderr_after_threshold(capsys) -> None:
    cfg = CliProgressConfig(enabled=True, threshold_seconds=0.01, interval_seconds=0.01)
    with cli_progress(command_name="task show", argv=["task", "show", "123"], config=cfg):
        time.sleep(0.06)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "still running" in captured.err


def test_cli_progress_disabled_is_silent(capsys) -> None:
    cfg = CliProgressConfig(enabled=False, threshold_seconds=0.0, interval_seconds=0.01)
    with cli_progress(command_name="task show", argv=["task", "show", "123"], config=cfg):
        time.sleep(0.03)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

