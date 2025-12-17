from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_run_git_command_rejects_checkout_and_switch(tmp_path: Path) -> None:
    from edison.core.utils.subprocess import run_git_command

    with pytest.raises(ValueError, match=r"Forbidden git branch switch"):
        run_git_command(["git", "checkout", "main"], cwd=tmp_path, check=False, capture_output=True)

    with pytest.raises(ValueError, match=r"Forbidden git branch switch"):
        run_git_command(["git", "switch", "main"], cwd=tmp_path, check=False, capture_output=True)


def test_run_git_command_does_not_block_non_git_commands(tmp_path: Path) -> None:
    from edison.core.utils.subprocess import run_git_command

    result = run_git_command(
        [sys.executable, "-c", "print('checkout')"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (result.stdout or "").strip() == "checkout"
