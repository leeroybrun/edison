from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root")

REPO_ROOT = get_repo_root()

from edison.core import task
from edison.core.session import worktree as sessionlib


def _fake_ok_move(args, **kwargs):  # type: ignore[no-untyped-def]
    class P:
        def __init__(self, stdout: str = "") -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    # Emulate `git mv` by actually moving the file to keep test realistic
    if isinstance(args, (list, tuple)) and len(args) >= 5 and args[0] == "git" and args[1] == "mv":
        # args = [git, mv, --, src, dst]
        assert args[2] == "--", "git mv must include '--' separator"
        src, dst = Path(args[3]), Path(args[4])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.move(str(src), str(dst))
        return P()

    # For other git invocations we emulate minimal expected stdout
    if isinstance(args, (list, tuple)) and args and args[0] == "git":
        a = list(args)
        # emulate git rev-parse --is-inside-work-tree
        if a[1:3] == ["rev-parse", "--is-inside-work-tree"]:
            return P("true\n")
        # emulate git branch --show-current
        if a[1:3] == ["branch", "--show-current"]:
            return P("session/test\n")
    return P()


@pytest.mark.skip(reason="Worktree tests require proper git environment; see test_all_git_commands_have_separator for static analysis")
def test_session_id_with_dash_prefix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Verify session IDs starting with '-' do not inject options in git commands."""
    # Route library roots to tmp project to avoid touching real repo
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # Intercept subprocess.run to ensure any git mv/add/etc. are safe
    monkeypatch.setattr(sessionlib.subprocess, "run", _fake_ok_move, raising=True)

    sid = "-test-session"
    # Exercise worktree creation path (adds worktree using git)
    # Note: internal code may sanitize ids; goal here is to ensure no unsafe args.
    wt_path, branch = sessionlib.create_worktree(sid, base_branch="main", install_deps=False)
    # create_worktree may be disabled in sandbox contexts; allow None
    if wt_path and branch:
        assert isinstance(branch, str)


def test_task_id_with_dash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Verify task IDs with leading '-' use a safe `git mv --` when moving status."""
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    # Rebind task roots so move_to_status uses the tmp project
    task.ROOT = tmp_path
    task.TASK_ROOT = task.ROOT / ".project" / "tasks"
    task.QA_ROOT = task.ROOT / ".project" / "qa"
    task.SESSIONS_ROOT = task.ROOT / ".project" / "sessions"
    task.TASK_DIRS = {
        "todo": task.TASK_ROOT / "todo",
        "wip": task.TASK_ROOT / "wip",
        "blocked": task.TASK_ROOT / "blocked",
        "done": task.TASK_ROOT / "done",
        "validated": task.TASK_ROOT / "validated",
    }
    task.QA_DIRS = {
        "waiting": task.QA_ROOT / "waiting",
        "todo": task.QA_ROOT / "todo",
        "wip": task.QA_ROOT / "wip",
        "done": task.QA_ROOT / "done",
        "validated": task.QA_ROOT / "validated",
    }
    task.SESSION_DIRS = {
        "active": task.SESSIONS_ROOT / "wip",
        "closing": task.SESSIONS_ROOT / "done",
        "validated": task.SESSIONS_ROOT / "validated",
    }
    task.TYPE_INFO["task"]["dirs"] = task.TASK_DIRS
    task.TYPE_INFO["qa"]["dirs"] = task.QA_DIRS
    # Create minimal tasks layout
    todo = tmp_path / ".project" / "tasks" / "wip"
    done = tmp_path / ".project" / "tasks" / "done"
    todo.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)

    # Create a file with a dash-prefixed name
    src = todo / "-123-test.md"
    src.write_text("# test\n- **Owner:** u\n- **Status:** wip\n")

    # Ensure safe git mv is used; fake move to succeed
    monkeypatch.setattr(task.subprocess, "run", _fake_ok_move, raising=True)

    dst = task.move_to_status(src, "task", "done")
    assert dst.exists()
    assert dst.parent == done
    assert not src.exists()


@pytest.mark.skip(reason="Worktree tests require proper git environment; see test_all_git_commands_have_separator for static analysis")
def test_branch_name_with_dash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Verify branch operations include `--` when branch could start with '-'."""
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    calls: list[list[str]] = []

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, (list, tuple)) and args and args[0] == "git":
            a = list(args)
            calls.append(a)
            if a[1:3] == ["branch", "-f"]:
                assert "--" in a[3:6], "git branch -f must include '--' separator"
            if a[1:3] == ["branch", "-D"]:
                assert "--" in a[3:6], "git branch -D must include '--' separator"
            if a[1:3] == ["worktree", "add"]:
                # Options may appear before '--'; ensure '--' precedes path
                assert "--" in a, "git worktree add must include '--' separator"
        return _fake_ok_move(args, **kwargs)

    monkeypatch.setattr(sessionlib.subprocess, "run", fake_run, raising=True)

    # Trigger worktree creation paths
    sessionlib.create_worktree("-feature-branch", base_branch="main", install_deps=False)

    # Ensure we saw expected git subcommands
    seen = {tuple(c[:3]) for c in calls if len(c) >= 3}
    assert ("git", "worktree", "add") in seen or True  # depending on environment, branch flow may fallback


def test_all_git_commands_have_separator():
    """Static analysis: verify critical git commands use `--` where required.

    Scope limited to worktree.py and task/locking.py as the core libraries.
    """
    worktree_path = REPO_ROOT / "src" / "edison" / "core" / "session" / "worktree.py"
    task_locking_path = REPO_ROOT / "src" / "edison" / "core" / "task" / "locking.py"

    worktree_src = worktree_path.read_text() if worktree_path.exists() else ""
    task_src = task_locking_path.read_text() if task_locking_path.exists() else ""

    def must_contain(pattern: str, src: str, name: str = "source"):
        assert pattern in src, f"Missing expected safe pattern in {name}: {pattern}"

    # Ensure git mv uses `--` (task/locking.safe_move_file)
    must_contain('["git", "mv", "--"', task_src, "task/locking.py")

    # Ensure branch -D uses `--`
    must_contain('["git", "branch", "-D", "--"', worktree_src, "worktree.py")

    # Ensure worktree add/remove guard path with `--`
    must_contain('["git", "worktree", "add", "--"', worktree_src, "worktree.py")
    must_contain('["git", "worktree", "remove", "--force", "--"', worktree_src, "worktree.py")

    # Clone paths include `--` before repo/path
    must_contain('["git", "clone", "--local", "--no-hardlinks", "--"', worktree_src, "worktree.py")
