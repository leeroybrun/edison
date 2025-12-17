from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def test_session_create_base_branch_override_sets_session_git_basebranch_and_does_not_switch_primary(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Create a feature branch in the primary checkout.
    _git(isolated_project_env, "checkout", "-b", "feature/session-create-override")
    (isolated_project_env / "feat.txt").write_text("feat", encoding="utf-8")
    _git(isolated_project_env, "add", "-A")
    _git(isolated_project_env, "commit", "-m", "feat commit")

    # Configure worktrees to default to current branch, but override in the CLI call.
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranchMode": "current",
                    "baseBranch": None,
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                }
            }
        ),
        encoding="utf-8",
    )

    primary_before = _git(isolated_project_env, "branch", "--show-current")
    assert primary_before == "feature/session-create-override"

    from edison.cli._dispatcher import main as cli_main

    code = cli_main(
        [
            "session",
            "create",
            "--session-id",
            "sess-branch-override",
            "--owner",
            "tester",
            "--base-branch",
            "main",
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out or "{}")
    session = payload.get("session") or {}
    git_meta = session.get("git") or {}
    assert git_meta.get("baseBranch") == "main"

    # Primary worktree branch must not be switched by session creation.
    assert _git(isolated_project_env, "branch", "--show-current") == primary_before
