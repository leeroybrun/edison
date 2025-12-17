from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest


def test_git_worktree_list_cli_handles_core_worktree_format(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`edison git worktree-list --json` should not crash on dict-based worktree entries."""
    worktree_path = tmp_path / "wt-feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/one", str(worktree_path)],
        cwd=isolated_project_env,
        check=True,
        capture_output=True,
        text=True,
    )

    from edison.cli.git.worktree_list import main as worktree_list_main

    args = argparse.Namespace(session=None, all=False, json=True)
    code = worktree_list_main(args)
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out or "{}")
    assert payload.get("total", 0) >= 2  # main checkout + feature worktree
    assert any(wt.get("branch") == "feature/one" for wt in payload.get("worktrees", []))
