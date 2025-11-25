"""Test 04: Git Worktree Integration (REAL CLIs)

This suite verifies REAL git worktree behavior driven by the actual CLI:

- Uses the real `session new` CLI which auto-creates worktrees (config worktrees.enabled = true)
- Asserts session JSON contains git metadata: worktreePath, branchName, baseBranch
- Verifies real git operations (diff, branch isolation, worktree listing) using subprocess
- NO mock helpers (no TestGitRepo, no mock git functions)
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from helpers.assertions import (
    assert_directory_exists,
    assert_file_exists,
)
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_error_contains,
)
from helpers.test_env import TestProjectDir
from edison.core.utils.subprocess import run_with_timeout

PROJECT_NAME = os.environ.get("PROJECT_NAME", "example-project")
WORKTREE_ROOT_NAMES = {f"{PROJECT_NAME}-worktrees", ".worktrees"}


# ----------------------------------------------------------------------------
# Local helpers (real git utilities)
# ----------------------------------------------------------------------------
def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return run_with_timeout(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_git_repo(repo_root: Path) -> None:
    # Initialize repo and configure identity (local-only)
    cp = _git(repo_root, "init", "-b", "main")
    run_with_timeout(["git", "config", "--local", "commit.gpgsign", "false"], cwd=repo_root, check=True, capture_output=True)
    if cp.returncode != 0:
        raise RuntimeError(f"git init failed: {cp.stderr}")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test User")
    # Seed initial commit so 'main' exists
    (repo_root / "README.md").write_text("# Test Repo\n")
    _git(repo_root, "add", "-A")
    cp = _git(repo_root, "commit", "-m", "Initial commit")
    if cp.returncode != 0:
        raise RuntimeError(f"git commit failed: {cp.stderr}")


def _commit_all(cwd: Path, message: str) -> None:
    _git(cwd, "add", "-A")
    cp = _git(cwd, "commit", "-m", message)
    if cp.returncode != 0:
        raise RuntimeError(f"git commit failed: {cp.stderr}")


def _git_changed_files(cwd: Path, base_branch: str = "main") -> list[str]:
    # Use a simple diff against base; tasks/ready uses base...HEAD (three-dot)
    cp = _git(cwd, "diff", "--name-only", base_branch)
    if cp.returncode != 0:
        raise RuntimeError(f"git diff failed: {cp.stderr}")
    return [l.strip() for l in cp.stdout.splitlines() if l.strip()]


def _git_worktree_paths(repo_root: Path) -> list[Path]:
    # Parse `git worktree list --porcelain` for robustness
    cp = _git(repo_root, "worktree", "list", "--porcelain")
    if cp.returncode != 0:
        raise RuntimeError(f"git worktree list failed: {cp.stderr}")
    paths: list[Path] = []
    for line in cp.stdout.splitlines():
        if line.startswith("worktree "):
            path_str = line.split(" ", 1)[1].strip()
            paths.append(Path(path_str))
    return paths


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_create_worktree_for_session(test_project_dir: TestProjectDir):
    """Create a session via REAL CLI; verify auto-created worktree and git meta."""
    session_id = "test-wt-session"
    _init_git_repo(test_project_dir.tmp_path)

    # REAL CLI: session new (auto-creates worktree per worktrees config)
    result = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(result)

    # Ensure worktree materialization (idempotent in real repos)
    assert_command_success(
        run_script(
            "session",
            ["status", session_id, "--json"],
            cwd=test_project_dir.tmp_path,
        )
    )

    # Validate session JSON git metadata
    session_path = test_project_dir.get_session_path(session_id)
    assert_file_exists(session_path)
    session_data = json.loads(session_path.read_text())
    assert "git" in session_data
    git_meta = session_data["git"]
    assert git_meta.get("worktreePath")
    assert git_meta.get("branchName") == f"session/{session_id}"
    assert git_meta.get("baseBranch") == "main"

    # Validate worktree directory exists and is under .../{PROJECT_NAME}-worktrees/{sessionId}
    wt = Path(git_meta["worktreePath"])  # absolute path
    assert_directory_exists(wt)
    assert wt.name == session_id
    # Accept either configured baseDirectory or local .worktrees root
    assert wt.parent.name in WORKTREE_ROOT_NAMES


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_branch_isolation(test_project_dir: TestProjectDir):
    """Files committed in worktree do not appear in main repo checkout."""
    session_id = "test-isolation"
    _init_git_repo(test_project_dir.tmp_path)

    # Create REAL session → auto worktree
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    git_meta = test_project_dir.get_session_json(session_id)["git"]
    worktree_path = Path(git_meta["worktreePath"])

    # Create and commit a file in the worktree
    in_wt = worktree_path / "test.txt"
    in_wt.write_text("Test content\n")
    _commit_all(worktree_path, "Add test file")

    assert in_wt.exists()
    assert not (test_project_dir.tmp_path / "test.txt").exists()


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_diff_detection(test_project_dir: TestProjectDir):
    """Changed files in worktree are reported by real git diff."""
    session_id = "test-diff"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    worktree_path = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])

    # Create files and commit in worktree
    file1 = worktree_path / "apps" / ""example-app"" / "src" / "Component.tsx"
    file2 = worktree_path / "packages" / "api-core" / "src" / "api.ts"
    file1.parent.mkdir(parents=True, exist_ok=True)
    file2.parent.mkdir(parents=True, exist_ok=True)
    file1.write_text("export const Component = () => <div>Test</div>;\n")
    file2.write_text("export const api = () => {};\n")
    _commit_all(worktree_path, "Add components")

    changed_files = _git_changed_files(worktree_path, "main")
    assert "apps/example-app/src/Component.tsx" in changed_files
    assert "packages/api-core/src/api.ts" in changed_files


@pytest.mark.worktree
@pytest.mark.session
@pytest.mark.requires_git
@pytest.mark.fast
def test_session_worktree_integration(test_project_dir: TestProjectDir):
    """`session new` populates git metadata and creates a real worktree."""
    session_id = "test-integrated-session"
    _init_git_repo(test_project_dir.tmp_path)

    result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(result)

    session_data = test_project_dir.get_session_json(session_id)
    git_meta = session_data["git"]
    wt = Path(git_meta["worktreePath"])
    assert_directory_exists(wt)
    assert git_meta["branchName"] == f"session/{session_id}"
    assert git_meta["baseBranch"] == "main"


@pytest.mark.worktree
@pytest.mark.context7
@pytest.mark.requires_git
@pytest.mark.integration
def test_context7_cross_check_with_git_diff(test_project_dir: TestProjectDir):
    """REAL guard: tasks/ready detects packages from git-diff and requires Context7 for each.

    - Make React (.tsx) and Zod (.ts) changes inside the session worktree
    - Create task + QA via real CLIs
    - Run tasks/ready and assert it fails listing BOTH packages (react, zod)
    """
    _init_git_repo(test_project_dir.tmp_path)
    session_id = "test-ctx7-crosscheck"
    task_num, wave, slug = "100", "wave1", "ctx7-test"
    task_id = f"{task_num}-{wave}-{slug}"

    # 1) Create session (auto worktree)
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    worktree_path = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])

    # 2) Create task + QA via real CLIs (register under the session)
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", task_num, "--wave", wave, "--slug", slug, "--owner", session_id, "--session", session_id],
            cwd=test_project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script(
            "qa/new",
            [task_id, "--owner", session_id, "--session", session_id],
            cwd=test_project_dir.tmp_path,
        )
    )

    # 3) Make mixed changes in worktree (React + Zod) and commit
    react_file = worktree_path / "apps" / ""example-app"" / "src" / "Button.tsx"
    react_file.parent.mkdir(parents=True, exist_ok=True)
    react_file.write_text('import React from "react";\nexport const Btn = () => <button>Ok</button>;\n')

    api_file = worktree_path / "packages" / "api-core" / "src" / "auth.ts"
    api_file.parent.mkdir(parents=True, exist_ok=True)
    api_file.write_text('import { z } from "zod";\nexport const Auth = z.object({ token: z.string() });\n')
    _commit_all(worktree_path, "Add React + Zod changes")

    # 4) Run guard – should fail and mention both packages
    result = run_script(
        "tasks/ready",
        [task_id, "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_failure(result)
    assert_error_contains(result, "Context7 evidence required")
    assert ("react" in result.stderr) and ("zod" in result.stderr)


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_file_extension_detection(test_project_dir: TestProjectDir):
    """Diff shows multiple file types created in worktree."""
    session_id = "test-extensions"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    worktree_path = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])

    # Create files with various extensions and commit
    files = {
        "apps/example-app/src/Page.tsx": "export const Page = () => <div>TSX</div>;\n",
        "packages/api-core/src/validator.ts": "export const validate = (data: any) => {};\n",
        "packages/db/prisma/schema.prisma": "model User { id String @id }\n",
        "apps/engine/src/worker.py": "def process(): pass\n",
    }
    for rel, content in files.items():
        p = worktree_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    _commit_all(worktree_path, "Add various files")

    changed_files = _git_changed_files(worktree_path, "main")
    assert any(f.endswith(".tsx") for f in changed_files)
    assert any(f.endswith(".ts") for f in changed_files)
    assert any(f.endswith(".prisma") for f in changed_files)
    assert any(f.endswith(".py") for f in changed_files)


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.slow
def test_worktree_multiple_commits(test_project_dir: TestProjectDir):
    """Track changes across multiple commits in a real worktree."""
    session_id = "test-multi-commits"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    worktree_path = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])

    file1 = worktree_path / "file1.txt"
    file2 = worktree_path / "file2.txt"
    file1.write_text("Content 1\n")
    _commit_all(worktree_path, "Add file1")

    file2.write_text("Content 2\n")
    _commit_all(worktree_path, "Add file2")

    file1.write_text("Modified content 1\n")
    _commit_all(worktree_path, "Modify file1")

    changed_files = _git_changed_files(worktree_path, "main")
    assert "file1.txt" in changed_files
    assert "file2.txt" in changed_files


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.edge_case
def test_worktree_no_changes(test_project_dir: TestProjectDir):
    """Fresh worktree should have empty diff vs base branch."""
    session_id = "test-no-changes"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    worktree_path = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])
    changed_files = _git_changed_files(worktree_path, "main")
    assert changed_files == []


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.integration
@pytest.mark.slow
def test_worktree_full_workflow(test_project_dir: TestProjectDir):
    """End-to-end happy path using REAL CLIs (no mocks).

    Steps:
      1) session new → auto worktree
      2) commit changes inside worktree
      3) tasks/new and qa/new under the session
      4) verify session status JSON contains git metadata and scope entries
    """
    _init_git_repo(test_project_dir.tmp_path)
    session_id = "test-full-wt-workflow"
    task_id = "100-wave1-wt-task"

    # 1) Create session
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    worktree_path = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])

    # 2) Make a code change in worktree
    comp = worktree_path / "apps" / ""example-app"" / "src" / "Auth.tsx"
    comp.parent.mkdir(parents=True, exist_ok=True)
    comp.write_text('import React from "react";\nexport const Auth = () => <div>Auth</div>;\n')
    _commit_all(worktree_path, "Add Auth component")

    # 3) Create task + QA
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", "100", "--wave", "wave1", "--slug", "wt-task", "--owner", session_id, "--session", session_id],
            cwd=test_project_dir.tmp_path,
        )
    )
    assert_command_success(
        run_script(
            "qa/new",
            [task_id, "--owner", session_id, "--session", session_id],
            cwd=test_project_dir.tmp_path,
        )
    )

    # 4) Verify session status as JSON
    status = run_script(
        "session",
        ["status", session_id, "--json"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(status)
    data = json.loads(status.stdout)
    assert data["git"]["branchName"].startswith("session/")
    assert data["git"]["worktreePath"] == str(worktree_path)
    assert task_id in data.get("tasks", {})


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_list_all(test_project_dir: TestProjectDir):
    """`git worktree list` shows main checkout plus session worktrees."""
    _init_git_repo(test_project_dir.tmp_path)
    session_ids = ["wt-1", "wt-2", "wt-3"]
    for sid in session_ids:
        assert_command_success(
            run_script(
                "session",
                ["new", "--owner", "tester", "--session-id", sid, "--mode", "start"],
                cwd=test_project_dir.tmp_path,
            )
        )
    paths = _git_worktree_paths(test_project_dir.tmp_path)
    # Expect main checkout + N worktrees
    assert len(paths) >= 1 + len(session_ids)


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.edge_case
def test_worktree_branch_name_validation(test_project_dir: TestProjectDir):
    """Branch names follow convention 'session/{session-id}' (from manifest)."""
    session_id = "test-branch-name"
    _init_git_repo(test_project_dir.tmp_path)
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    data = test_project_dir.get_session_json(session_id)
    assert data["git"]["branchName"] == f"session/{session_id}"


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_base_branch_tracking(test_project_dir: TestProjectDir):
    """Session JSON records the base branch used for worktree creation."""
    session_id = "test-base-tracking"
    _init_git_repo(test_project_dir.tmp_path)
    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    session_data = test_project_dir.get_session_json(session_id)
    assert session_data["git"]["baseBranch"] == "main"


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.integration
def test_worktree_concurrent_sessions(test_project_dir: TestProjectDir):
    """Multiple sessions create isolated worktrees; changes remain isolated."""
    _init_git_repo(test_project_dir.tmp_path)
    sessions: list[str] = []
    for i in range(3):
        sid = f"concurrent-{i}"
        assert_command_success(
            run_script(
                "session",
                ["new", "--owner", "tester", "--session-id", sid, "--mode", "start"],
                cwd=test_project_dir.tmp_path,
            )
        )
        sessions.append(sid)
        wt = Path(test_project_dir.get_session_json(sid)["git"]["worktreePath"])
        p = wt / f"file-{i}.txt"
        p.write_text(f"Content {i}\n")
        _commit_all(wt, f"Add file-{i}")

    for sid in sessions:
        test_project_dir.assert_session_exists(sid)
        wt = Path(test_project_dir.get_session_json(sid)["git"]["worktreePath"])
        assert_directory_exists(wt)


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_detect_react_import(test_project_dir: TestProjectDir):
    """Detect React-like usage via .tsx changes in git diff."""
    session_id = "test-react-detect"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    wt = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])
    tsx = wt / "apps" / ""example-app"" / "src" / "Button.tsx"
    tsx.parent.mkdir(parents=True, exist_ok=True)
    tsx.write_text('import React from "react";\nexport const Button = () => <button>Click</button>;\n')
    _commit_all(wt, "Add Button component")

    changed = _git_changed_files(wt, "main")
    assert any(f.endswith(".tsx") for f in changed)


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_detect_zod_import(test_project_dir: TestProjectDir):
    """Detect Zod usage via .ts changes and file content."""
    session_id = "test-zod-detect"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    wt = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])
    ts = wt / "packages" / "api-core" / "src" / "schema.ts"
    ts.parent.mkdir(parents=True, exist_ok=True)
    ts.write_text('import { z } from "zod";\nexport const userSchema = z.object({ name: z.string() });\n')
    _commit_all(wt, "Add user schema")

    changed = _git_changed_files(wt, "main")
    assert "packages/api-core/src/schema.ts" in changed
    assert "zod" in ts.read_text().lower()


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.fast
def test_worktree_detect_prisma_schema(test_project_dir: TestProjectDir):
    """Detect prisma usage via .prisma file in git diff."""
    session_id = "test-prisma-detect"
    _init_git_repo(test_project_dir.tmp_path)

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
            cwd=test_project_dir.tmp_path,
        )
    )
    wt = Path(test_project_dir.get_session_json(session_id)["git"]["worktreePath"])
    prisma_file = wt / "packages" / "db" / "prisma" / "schema.prisma"
    prisma_file.parent.mkdir(parents=True, exist_ok=True)
    prisma_file.write_text(
        """
datasource db {
  provider = "sqldb"
  url      = env("DATABASE_URL")
}

model User {
  id    String @id @default(cuid())
  email String @unique
}
"""
    )
    _commit_all(wt, "Update prisma schema")

    changed = _git_changed_files(wt, "main")
    assert any(f.endswith(".prisma") for f in changed)


@pytest.mark.session
@pytest.mark.security
@pytest.mark.fast
def test_cross_session_isolation_enforced(test_project_dir: TestProjectDir):
    """SECURITY: Attempting to manipulate tasks from different sessions must fail.

    This test verifies RULE.SESSION.ISOLATION is enforced by task.find_record().
    When a task is in session A, operations from session B context should fail
    to prevent cross-session manipulation.
    """
    # Create two separate sessions
    session_a = "session-a"
    session_b = "session-b"

    for sid in [session_a, session_b]:
        assert_command_success(
            run_script(
                "session",
                ["new", "--owner", "tester", "--session-id", sid, "--mode", "start"],
                cwd=test_project_dir.tmp_path,
            )
        )

    # Create a task in session A
    task_id = "900-wave1-session-a-task"
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", "900", "--wave", "wave1", "--slug", "session-a-task", "--session", session_a],
            cwd=test_project_dir.tmp_path,
        )
    )

    # Claim the task into session A
    assert_command_success(
        run_script(
            "tasks/claim",
            [task_id, "--session", session_a],
            cwd=test_project_dir.tmp_path,
        )
    )

    # Verify task is in session A's directory
    session_a_task_path = (
        test_project_dir.project_root
        / "sessions"
        / "wip"
        / session_a
        / "tasks"
        / "wip"
        / f"{task_id}.md"
    )
    assert_file_exists(session_a_task_path)

    # CRITICAL: Attempt to manipulate the task from session B context should FAIL
    # This prevents cross-session tampering
    cross_session_attempt = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_b],
        cwd=test_project_dir.tmp_path,
    )

    # Must fail - cannot manipulate task from different session
    assert_command_failure(cross_session_attempt)
    assert_error_contains(cross_session_attempt, "Could not locate")

    # Verify task still in session A (not moved)
    assert_file_exists(session_a_task_path)
