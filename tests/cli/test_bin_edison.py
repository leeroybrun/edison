from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.requires_git
@pytest.mark.worktree
def test_bin_edison_uses_worktree_checkout_as_cwd(tmp_path: Path) -> None:
    """
    Validate that bin/edison runs target commands from the actual worktree root,
    not the internal .git/worktrees directory.
    """
    edison_home = tmp_path / "edison_home"
    scripts_dir = edison_home / "core" / "scripts"
    scripts_dir.mkdir(parents=True)

    # Minimal target command that prints its working directory.
    cmd = scripts_dir / "print_cwd"
    cmd.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        "sys.stdout.write(os.getcwd())\n"
    )
    cmd.chmod(0o755)

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "ci@example.com"], cwd=repo_root, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "CI"], cwd=repo_root, check=True
    )

    (repo_root / "README.md").write_text("demo\n")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=repo_root, check=True)

    worktree_root = tmp_path / "repo-worktree"
    subprocess.run(
        ["git", "worktree", "add", "-b", "wt-branch", str(worktree_root), "HEAD"],
        cwd=repo_root,
        check=True,
    )

    bin_path = Path(__file__).resolve().parents[3] / "bin" / "edison"

    env = os.environ.copy()
    env["EDISON_HOME"] = str(edison_home)

    result = subprocess.run(
        [str(bin_path), "print_cwd"],
        cwd=worktree_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == worktree_root.resolve()
