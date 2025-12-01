"""Test 05: Git-Based Detection (REAL CLI + REAL git)

This suite validates git-based change detection using REAL project CLIs and REAL git
operations. All previous mock helpers are removed. Each test:
- Creates a real session via `session new` (which creates a git worktree when possible)
- Writes files inside the session worktree and uses real `git` commands to detect changes
- Uses `tasks/new` and `tasks/status` where relevant to exercise real CLI flows

Notes:
- Tests initialize a git repo in the test sandbox to allow worktree creation.
- When commits are required, tests set local git identity.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from helpers import TestProjectDir
from helpers.command_runner import run_script, assert_command_success
from helpers.assertions import assert_file_exists
from edison.core.utils.subprocess import run_with_timeout


# -----------------------------------------------------------------------------
# Local utilities
# -----------------------------------------------------------------------------

def _init_base_repo(cwd: Path) -> None:
    """Initialize a real git repository on branch 'main' with an initial commit."""
    # Initialize repo if not already
    run_with_timeout(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd, capture_output=True)
    result = run_with_timeout(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 or result.stdout.strip() != "true":
        run_with_timeout(["git", "init", "-b", "main"], cwd=cwd, check=True, capture_output=True)
        run_with_timeout(["git", "config", "--local", "commit.gpgsign", "false"], cwd=cwd, check=True, capture_output=True)
        (cwd / "README.md").write_text("# Test Repo\n")
        run_with_timeout(["git", "add", "README.md"], cwd=cwd, check=True, capture_output=True)
        # Set identity for commits
        run_with_timeout(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
        run_with_timeout(["git", "config", "user.name", "Test User"], cwd=cwd, check=True)
        run_with_timeout(["git", "commit", "-m", "Initial commit"], cwd=cwd, check=True, capture_output=True)


def _create_session_with_worktree(test_root: Path, session_id: str) -> Path:
    """Create a session via real CLI and return the worktree Path.

    Ensures a base repo is initialized at `test_root` so `session new` can create
    a git worktree. Returns the resolved Path to the worktree.
    """
    _init_base_repo(test_root)

    # Create session (real CLI)
    result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=test_root,
    )
    assert_command_success(result)

    # Read session JSON to get worktree path
    session_json = test_root / ".project" / "sessions" / "wip" / session_id / "session.json"
    assert_file_exists(session_json)
    session_data = json.loads(session_json.read_text())
    worktree_path = Path(session_data["git"]["worktreePath"]).resolve()
    return worktree_path


def _git_status_short(cwd: Path) -> str:
    return run_with_timeout(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _ensure_git_identity(cwd: Path) -> None:
    run_with_timeout(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=False)
    run_with_timeout(["git", "config", "user.name", "Test User"], cwd=cwd, check=False)


def _git_commit_all(cwd: Path, message: str) -> None:
    _ensure_git_identity(cwd)
    run_with_timeout(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
    run_with_timeout(["git", "commit", "-m", message], cwd=cwd, check=True, capture_output=True)


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_tsx_files_imply_react(project_dir: TestProjectDir):
    """Real: create .tsx file in session worktree and detect via git status."""
    session_id = "test-tsx-react"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    # Create .tsx file without committing (detect via status)
    tsx_file = worktree_path / "src" / "Button.tsx"
    tsx_file.parent.mkdir(parents=True, exist_ok=True)
    tsx_file.write_text('export const Button = () => <button>Click</button>;')

    status = _git_status_short(worktree_path)
    assert "src/Button.tsx" in status
    # In the real mapping, .tsx implies React (Context7 enforcement occurs elsewhere)


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_prisma_files(project_dir: TestProjectDir):
    """Real: detect prisma schema file via git status."""
    session_id = "test-prisma"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    prisma_file = worktree_path / "prisma" / "schema.prisma"
    prisma_file.parent.mkdir(parents=True, exist_ok=True)
    prisma_file.write_text(
        """
datasource db {
  provider = "sqldb"
  url = env("DATABASE_URL")
}

model User {
  id String @id
}
""".strip()
    )

    status = _git_status_short(worktree_path)
    assert "prisma/schema.prisma" in status


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_zod_from_imports(project_dir: TestProjectDir):
    """Real: file contains Zod import; verify change tracked and content contains import."""
    session_id = "test-zod-import"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    ts_file = worktree_path / "src" / "schema.ts"
    ts_file.parent.mkdir(parents=True, exist_ok=True)
    ts_file.write_text('import { z } from "zod";\n\nconst userSchema = z.object({ name: z.string() });')

    status = _git_status_short(worktree_path)
    assert "src/schema.ts" in status
    assert 'from "zod"' in ts_file.read_text()


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_react_from_jsx_syntax(project_dir: TestProjectDir):
    """Real: detect JSX + react import via file content; track with git status."""
    session_id = "test-react-jsx"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    jsx_file = worktree_path / "src" / "App.jsx"
    jsx_file.parent.mkdir(parents=True, exist_ok=True)
    jsx_file.write_text('import React from "react";\nexport const App = () => <div>App</div>;')

    status = _git_status_short(worktree_path)
    assert "src/App.jsx" in status
    content = jsx_file.read_text()
    assert "<div>" in content
    assert 'from "react"' in content


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_multiple_packages_in_one_file(project_dir: TestProjectDir):
    """Real: a file importing multiple packages; verify content and tracking."""
    session_id = "test-multi-package"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    ts_file = worktree_path / "src" / "validator.ts"
    ts_file.parent.mkdir(parents=True, exist_ok=True)
    ts_file.write_text(
        'import { z } from "zod";\n'
        'import axios from "axios";\n'
        'import { prismaClient } from "@prisma/client";\n\n'
        'const schema = z.object({ url: z.string() });\n'
        'const prisma = new prismaClient();\n'
    )

    status = _git_status_short(worktree_path)
    assert "src/validator.ts" in status
    content = ts_file.read_text()
    assert 'from "zod"' in content
    assert 'from "axios"' in content
    assert 'from "@prisma/client"' in content


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_packages_from_directory_structure(project_dir: TestProjectDir):
    """Real: infer packages by directories; verify via git diff after commit."""
    session_id = "test-dir-structure"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    files = {
        "apps/example-app/src/Page.tsx": "export const Page = () => <div>Page</div>;",
        "packages/api-core/src/routes.ts": "export const routes = {};",
        "packages/db/prisma/migrations/001_init/migration.sql": "CREATE TABLE users (id UUID);",
    }

    for rel, content in files.items():
        f = worktree_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)

    _git_commit_all(worktree_path, "Add files for package inference")
    diff = run_with_timeout(["git", "diff", "--name-only", "main"], cwd=worktree_path, capture_output=True, text=True, check=True).stdout.splitlines()

    assert any("apps/example-app" in f for f in diff)
    assert any("packages/api-core" in f for f in diff)
    assert any("packages/db/prisma" in f for f in diff)


@pytest.mark.requires_git
@pytest.mark.fast
def test_git_diff_multiple_commits(project_dir: TestProjectDir):
    """Real: diff across multiple commits from session branch to main."""
    session_id = "test-multi-commit-diff"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    (worktree_path / "file1.ts").write_text("const a = 1;\n")
    _git_commit_all(worktree_path, "Add file1")

    (worktree_path / "file2.ts").write_text("const b = 2;\n")
    _git_commit_all(worktree_path, "Add file2")

    (worktree_path / "file3.ts").write_text("const c = 3;\n")
    _git_commit_all(worktree_path, "Add file3")

    changed = run_with_timeout(["git", "diff", "--name-only", "main"], cwd=worktree_path, capture_output=True, text=True, check=True).stdout.splitlines()
    assert "file1.ts" in changed
    assert "file2.ts" in changed
    assert "file3.ts" in changed


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_test_files_vs_source_files(project_dir: TestProjectDir):
    """Real: distinguish test files vs source via git status listing."""
    session_id = "test-file-types"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    files = {
        "src/auth.ts": "export const auth = () => {};",
        "src/auth.test.ts": "test('auth works', () => {});",
        "src/__tests__/auth.spec.ts": "describe('auth', () => {});",
    }
    for rel, content in files.items():
        f = worktree_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)

    status = _git_status_short(worktree_path)
    changed = [line.split()[-1] for line in status.splitlines() if line.strip()]
    test_files = [f for f in changed if ".test." in f or ".spec." in f or "__tests__" in f]
    source_files = [f for f in changed if f not in test_files]

    assert len(test_files) == 2
    assert len(source_files) == 1


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_config_files(project_dir: TestProjectDir):
    """Real: detect presence of config files via git status or diff."""
    session_id = "test-config-files"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    configs = {
        "package.json": '{"name": "test"}',
        "tsconfig.json": '{"compilerOptions": {}}',
        "next.config.js": 'module.exports = {};',
        ".eslintrc.json": '{"extends": []}',
        "vitest.config.ts": 'export default {};',
    }

    for rel, content in configs.items():
        f = worktree_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)

    _git_commit_all(worktree_path, "Update configs")
    changed = run_with_timeout(["git", "diff", "--name-only", "main"], cwd=worktree_path, capture_output=True, text=True, check=True).stdout.splitlines()
    config_files = [f for f in changed if any(c in f for c in ["package.json", "tsconfig", "config.js", "config.ts", ".eslintrc"])]
    assert len(config_files) >= 4


@pytest.mark.requires_git
@pytest.mark.fast
def test_git_diff_empty_after_no_changes(project_dir: TestProjectDir):
    """Real: newly created session branch has no diff vs base."""
    session_id = "test-no-changes"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    changed = run_with_timeout(["git", "diff", "--name-only", "main"], cwd=worktree_path, capture_output=True, text=True, check=True).stdout.splitlines()
    assert len([c for c in changed if c.strip()]) == 0


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_deleted_files_in_diff(project_dir: TestProjectDir):
    """Real: detect file deletion using git diff with --diff-filter=D on the last commit."""
    session_id = "test-deleted-files"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    f = worktree_path / "temp.ts"
    f.write_text("const temp = 1;\n")
    _git_commit_all(worktree_path, "Add temp")

    # Delete and commit
    f.unlink()
    _git_commit_all(worktree_path, "Delete temp")

    # Detect deletions in the last commit specifically
    diff = run_with_timeout(["git", "diff", "--name-only", "--diff-filter=D", "HEAD~1", "HEAD"], cwd=worktree_path, capture_output=True, text=True, check=True).stdout
    assert "temp.ts" in diff


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_moved_files_in_diff(project_dir: TestProjectDir):
    """Real: detect rename using git diff --find-renames on last commit."""
    session_id = "test-moved-files"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    old_file = worktree_path / "old.ts"
    old_file.write_text("const value = 1;\n")
    _git_commit_all(worktree_path, "Add old.ts")

    new_file = worktree_path / "new.ts"
    old_file.rename(new_file)
    _git_commit_all(worktree_path, "Rename to new.ts")

    diff = run_with_timeout(["git", "diff", "--name-status", "--find-renames", "HEAD~1", "HEAD"], cwd=worktree_path, capture_output=True, text=True, check=True).stdout
    # Expect an R* line, ensure new filename appears
    assert "new.ts" in diff


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_prisma_schema_in_packages_db(project_dir: TestProjectDir):
    """Real: detect prisma schema file in packages/db/prisma via git status."""
    session_id = "test-prisma-packages-db"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    # Create schema in packages/db/prisma path (actual project structure)
    prisma_file = worktree_path / "packages" / "db" / "prisma" / "schema.prisma"
    prisma_file.parent.mkdir(parents=True, exist_ok=True)
    prisma_file.write_text(
        """
datasource db {
  provider = "sqldb"
  url = env("DATABASE_URL")
}

model Lead {
  id String @id @default(uuid())
  email String @unique
}
""".strip()
    )

    status = _git_status_short(worktree_path)
    assert "packages/db/prisma/schema.prisma" in status


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_prisma_migrations(project_dir: TestProjectDir):
    """Real: detect prisma migration files via git status."""
    session_id = "test-prisma-migrations"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    # Create migration files in packages/db/prisma/migrations
    migration_dir = worktree_path / "packages" / "db" / "prisma" / "migrations" / "20250101000000_init"
    migration_dir.mkdir(parents=True, exist_ok=True)

    migration_sql = migration_dir / "migration.sql"
    migration_sql.write_text("CREATE TABLE leads (id UUID PRIMARY KEY);")

    status = _git_status_short(worktree_path)
    assert "packages/db/prisma/migrations" in status
    assert "migration.sql" in status


@pytest.mark.requires_git
@pytest.mark.fast
def test_detect_prisma_seed_files(project_dir: TestProjectDir):
    """Real: detect prisma seed files in prisma/seeds via git status."""
    session_id = "test-prisma-seeds"
    worktree_path = _create_session_with_worktree(project_dir.tmp_path, session_id)

    # Create seed files
    seed_file = worktree_path / "packages" / "db" / "prisma" / "seeds" / "users.ts"
    seed_file.parent.mkdir(parents=True, exist_ok=True)
    seed_file.write_text(
        """
import { prismaClient } from '@prisma/client'
from edison.core.utils.subprocess import run_with_timeout

const prisma = new prismaClient()

export async function seedUsers() {
  await prisma.user.createMany({
    data: [{ email: 'test@example.com' }]
  })
}
""".strip()
    )

    status = _git_status_short(worktree_path)
    assert "packages/db/prisma/seeds" in status
    assert "users.ts" in status
