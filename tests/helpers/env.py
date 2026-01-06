"""Test environment helpers for E2E workflow tests.

Current Edison project layout:
- Project root contains `.project/` for tasks/qa/sessions data
- Project root contains `.edison/` for configuration and generated artifacts
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.path_utils import find_in_states, get_record_state
from tests.helpers.file_utils import copy_if_different, copy_tree_if_different
from tests.helpers.markdown_utils import parse_task_metadata, parse_qa_metadata
from tests.config import get_task_states, get_qa_states, get_session_states, load_paths, get_env_var_name


class TestProjectDir:
    """Isolated .project directory with helper methods for testing."""

    __test__ = False  # Tell pytest this is not a test class

    def __init__(self, tmp_path: Path, repo_root: Path):
        """Initialize test project directory.

        Args:
            tmp_path: pytest tmp_path fixture (temporary directory)
            repo_root: Path to actual repository root (for copying configs)
        """
        self.tmp_path = tmp_path
        self.repo_root = repo_root
        self.project_root = tmp_path / ".project"
        self.edison_root = tmp_path / ".edison"

        # Setup directory structure
        self._setup_directories()
        self._setup_configs()

    def _setup_directories(self) -> None:
        """Create `.project/` and `.edison/` directory structure."""
        # Load states and paths from YAML config (NO hardcoded values)
        task_states = get_task_states()
        qa_states = get_qa_states()
        session_states = get_session_states()
        paths_config = load_paths()

        # Get subdirectory names from config
        project_subdirs = paths_config["subdirectories"]["project"]
        edison_subdirs = paths_config["subdirectories"]["edison"]
        qa_subdirs = paths_config["subdirectories"]["qa"]

        # .project structure - tasks
        for state in task_states:
            (self.project_root / project_subdirs["tasks"] / state).mkdir(parents=True, exist_ok=True)

        # .project structure - qa
        for state in qa_states:
            (self.project_root / project_subdirs["qa"] / state).mkdir(parents=True, exist_ok=True)
        (self.project_root / project_subdirs["qa"] / qa_subdirs["validation_evidence"]).mkdir(parents=True, exist_ok=True)

        # .project structure - sessions
        for state in session_states:
            (self.project_root / project_subdirs["sessions"] / state).mkdir(parents=True, exist_ok=True)

        # .edison structure (config + session templates expected by SessionConfig)
        (self.edison_root / edison_subdirs["config"]).mkdir(parents=True, exist_ok=True)
        (self.edison_root / edison_subdirs["_generated"]).mkdir(parents=True, exist_ok=True)
        (self.edison_root / edison_subdirs["packs"]).mkdir(parents=True, exist_ok=True)
        (self.edison_root / edison_subdirs["sessions"]).mkdir(parents=True, exist_ok=True)

    def _setup_configs(self) -> None:
        """Copy/create necessary config files."""
        # Skip copying if repo_root is the same as tmp_path (already set up by fixture)
        if self.repo_root.resolve() == self.tmp_path.resolve():
            return

        # Copy `.edison/config/*` overrides (if present) from the repo under test.
        src_config_dir = self.repo_root / ".edison" / "config"
        if src_config_dir.exists():
            copy_tree_if_different(src_config_dir, self.edison_root / "config")

        # E2E tests exercise the full "web-stack" workflow (worktrees, Context7 triggers,
        # evidence requirements) and must not inherit the Edison repo's own pack list.
        # Keep the test environment deterministic and representative of real projects.
        packs_path = self.edison_root / "config" / "packs.yaml"
        packs_path.write_text(
            "packs:\n"
            "  active:\n"
            "    - nextjs\n"
            "    - react\n"
            "    - zod\n"
            "    - prisma\n"
            "    - fastify\n"
            "    - tailwind\n"
            "    - motion\n"
            "    - vitest\n"
            "    - typescript\n"
            "    - better-auth\n"
            "  autoActivate: true\n",
            encoding="utf-8",
        )

        # Some scenarios patch `.edison/manifest.json` to validate legacy override behavior.
        manifest_path = self.edison_root / "manifest.json"
        if not manifest_path.exists():
            manifest_path.write_text("{}", encoding="utf-8")

        # NOTE: Session workflow is now defined in bundled state-machine.yaml
        # and accessed via WorkflowConfig domain config. No need to create
        # legacy session-workflow.json files.

        # Copy task template if exists in the repo under test, otherwise create fallback.
        src_template = self.repo_root / ".project" / "tasks" / "TEMPLATE.md"
        dst_template = self.project_root / "tasks" / "TEMPLATE.md"
        if src_template.exists():
            shutil.copy(src_template, dst_template)
        else:
            # Fallback: create minimal task template for tests
            dst_template.write_text(
                "# Task Template\n\n"
                "## Metadata\n"
                "- **Task ID:** example-id\n"
                "- **Status:** todo\n",
                encoding="utf-8",
            )

        # Copy QA template if exists in the repo under test, otherwise create fallback.
        src_qa_template = self.repo_root / ".project" / "qa" / "TEMPLATE.md"
        dst_qa_template = self.project_root / "qa" / "TEMPLATE.md"
        if src_qa_template.exists():
            shutil.copy(src_qa_template, dst_qa_template)
        else:
            # Fallback: create minimal QA template for tests
            dst_qa_template.write_text(
                "# QA Template\n\n"
                "## Metadata\n"
                "- **Validator Owner:** _unassigned_\n"
                "- **Status:** waiting\n",
                encoding="utf-8",
            )

        # Ensure session template exists where SessionConfig.get_template_path() expects it:
        # `<project-root>/.edison/sessions/TEMPLATE.json`
        from edison.data import get_data_path
        src_session_template = get_data_path("templates", "session.template.json")
        if src_session_template.exists():
            dst_session_template = self.edison_root / "sessions" / "TEMPLATE.json"
            copy_if_different(src_session_template, dst_session_template)

    # === Command Execution ===

    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        check: bool = False,
        env: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """Run a command with the test environment.

        Args:
            cmd: Command and arguments
            cwd: Working directory (defaults to tmp_path)
            check: Raise exception on non-zero exit
            env: Environment variables to add/override

        Returns:
            CompletedProcess with stdout, stderr, returncode
        """
        if cwd is None:
            cwd = self.tmp_path

        # Add repo root to PATH so scripts can be found
        import os
        test_env = os.environ.copy()
        if env:
            test_env.update(env)

        result = run_with_timeout(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=test_env
        )
        return result

    # === State Queries ===

    def get_task_path(self, task_id: str) -> Optional[Path]:
        """Find task file by ID across all state directories.

        Args:
            task_id: Task ID (e.g., "150-wave1-auth")

        Returns:
            Path to task file, or None if not found
        """
        return find_in_states(self.project_root, task_id, "tasks", suffix=".md")

    def get_task_state(self, task_id: str) -> Optional[str]:
        """Get current state of a task.

        Args:
            task_id: Task ID

        Returns:
            State name (todo/wip/done/validated/blocked) or None if not found
        """
        return get_record_state(self.project_root, task_id, "tasks", suffix=".md")

    def get_task_json(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Parse task file as structured data.

        Args:
            task_id: Task ID

        Returns:
            Parsed task metadata, or None if not found/parseable
        """
        task_path = self.get_task_path(task_id)
        if not task_path:
            return None

        # Parse markdown frontmatter and content
        content = task_path.read_text()
        return parse_task_metadata(content, task_id, self.get_task_state(task_id))

    def get_qa_path(self, qa_id: str) -> Optional[Path]:
        """Find QA file by ID across all state directories."""
        return find_in_states(self.project_root, qa_id, "qa", suffix="-qa.md")

    def get_qa_state(self, qa_id: str) -> Optional[str]:
        """Get current state of a QA file."""
        return get_record_state(self.project_root, qa_id, "qa", suffix="-qa.md")

    def get_qa_json(self, qa_id: str) -> Optional[Dict[str, Any]]:
        """Parse QA file as structured data."""
        qa_path = self.get_qa_path(qa_id)
        if not qa_path:
            return None

        content = qa_path.read_text()
        return parse_qa_metadata(content, qa_id, self.get_qa_state(qa_id))

    def get_session_path(self, session_id: str) -> Optional[Path]:
        """Find session file by ID."""
        # Load session states from YAML config (NO hardcoded values)
        session_states = get_session_states()
        for state_dir in session_states:
            session_path = self.project_root / "sessions" / state_dir / session_id / "session.json"
            if session_path.exists():
                return session_path
        return None

    def get_session_json(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session JSON file."""
        session_path = self.get_session_path(session_id)
        if not session_path:
            return None

        return json.loads(session_path.read_text())

    def get_worktree_path(self, session_id: str) -> Optional[Path]:
        """Get worktree path for a session."""
        session = self.get_session_json(session_id)
        if session and "git" in session and "worktreePath" in session["git"]:
            return Path(session["git"]["worktreePath"])
        return None

    # === Assertions ===

    def assert_task_in_state(self, task_id: str, expected_state: str) -> None:
        """Assert task is in expected state."""
        actual_state = self.get_task_state(task_id)
        assert actual_state == expected_state, (
            f"Task {task_id} expected in {expected_state}, "
            f"but found in {actual_state}"
        )

    def assert_qa_in_state(self, qa_id: str, expected_state: str) -> None:
        """Assert QA is in expected state."""
        actual_state = self.get_qa_state(qa_id)
        assert actual_state == expected_state, (
            f"QA {qa_id} expected in {expected_state}, "
            f"but found in {actual_state}"
        )

    def assert_session_exists(self, session_id: str) -> None:
        """Assert session exists."""
        session_path = self.get_session_path(session_id)
        assert session_path is not None, f"Session {session_id} not found"
        assert session_path.exists(), f"Session file {session_path} does not exist"

    def assert_evidence_exists(self, task_id: str, filename: str, round_num: int = 1) -> None:
        """Assert evidence file exists for task."""
        # Load paths from config (NO hardcoded values)
        paths_config = load_paths()
        project_subdirs = paths_config["subdirectories"]["project"]
        qa_subdirs = paths_config["subdirectories"]["qa"]

        evidence_dir = (
            self.project_root / project_subdirs["qa"] / qa_subdirs["validation_evidence"] /
            task_id / f"round-{round_num}"
        )
        evidence_file = evidence_dir / filename
        assert evidence_file.exists(), (
            f"Evidence file {filename} not found in {evidence_dir}"
        )

    # === Test Data Creation ===

    def add_context7_evidence(
        self,
        task_id: str,
        package: str,
        round_num: int = 1
    ) -> Path:
        """Add Context7 evidence marker for a package.

        Args:
            task_id: Task ID
            package: Package name (e.g., 'react', 'zod')
            round_num: Round number

        Returns:
            Path to context7 marker file
        """
        # Load paths from config (NO hardcoded values)
        paths_config = load_paths()
        project_subdirs = paths_config["subdirectories"]["project"]
        qa_subdirs = paths_config["subdirectories"]["qa"]

        evidence_dir = (
            self.project_root / project_subdirs["qa"] / qa_subdirs["validation_evidence"] /
            task_id / f"round-{round_num}"
        )
        evidence_dir.mkdir(parents=True, exist_ok=True)

        marker_file = evidence_dir / f"context7-{package}.txt"
        from datetime import datetime
        marker_file.write_text(
            f"Context7 evidence for {package}\n"
            f"Retrieved: {datetime.utcnow().isoformat()}\n"
            f"Package: {package}\n"
        )
        return marker_file


def create_tdd_evidence(
    project: TestProjectDir,
    session_id: str,
    task_id: str,
    *,
    test_commit: str,
    impl_commit: str,
    refactor_commit: Optional[str] = None,
    red_ts: Optional[float] = None,
    green_ts: Optional[float] = None,
    refactor_ts: Optional[float] = None,
) -> Path:
    """Create TDD evidence files for a session/task round.

    Files are written under:
    .project/sessions/{state}/{session_id}/tasks/{task_id}/evidence/tdd/round-1
    """
    # Load default session state and paths from config (NO hardcoded values)
    from tests.config import get_default_value, load_paths
    import time

    default_state = get_default_value("session", "state")
    paths_config = load_paths()
    project_subdirs = paths_config["subdirectories"]["project"]

    evidence_dir = (
        project.project_root
        / project_subdirs["sessions"]
        / default_state
        / session_id
        / project_subdirs["tasks"]
        / task_id
        / "evidence"
        / "tdd"
        / "round-1"
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)

    red_time = red_ts if red_ts is not None else time.time()
    green_time = green_ts if green_ts is not None else red_time + 5
    (evidence_dir / "red-timestamp.txt").write_text(str(red_time))
    (evidence_dir / "green-timestamp.txt").write_text(str(green_time))
    (evidence_dir / "test-commit.txt").write_text(test_commit)
    (evidence_dir / "impl-commit.txt").write_text(impl_commit)

    if refactor_commit:
        ref_time = refactor_ts if refactor_ts is not None else green_time + 5
        (evidence_dir / "refactor-timestamp.txt").write_text(str(ref_time))
        (evidence_dir / "refactor-commit.txt").write_text(refactor_commit)

    return evidence_dir


class TestGitRepo:
    """Isolated git repository for worktree testing."""

    __test__ = False  # Tell pytest this is not a test class

    def __init__(self, tmp_path: Path, *, init_repo: bool = True):
        """Initialize test git repository.

        Args:
            tmp_path: pytest tmp_path fixture (temporary directory)
            init_repo: When False, assumes the repository already exists at tmp_path
                (i.e. `.git/` is present) and skips `git init` + initial commit.
        """
        self.repo_path = tmp_path
        self.worktrees_path = tmp_path / ".worktrees"
        self.worktrees_path.mkdir(exist_ok=True)

        if init_repo:
            self._init_repo()
        else:
            if not (self.repo_path / ".git").exists():
                raise ValueError(
                    f"init_repo=False but no git repository found at {self.repo_path}"
                )

    def _init_repo(self) -> None:
        """Initialize git repository with main branch."""
        run_with_timeout(
            ["git", "init", "-b", "main"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        # Configure identity for commits in test repos to be hermetic.
        run_with_timeout(
            ["git", "config", "--local", "user.email", "test@example.com"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )
        run_with_timeout(
            ["git", "config", "--local", "user.name", "Test User"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        # Disable commit signing in test repos (prevents SSH signing errors)
        run_with_timeout(
            ["git", "config", "--local", "commit.gpgsign", "false"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        # Create initial commit
        readme = self.repo_path / "README.md"
        readme.write_text("# Test Repository\n")

        run_with_timeout(
            ["git", "add", "README.md"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )
        run_with_timeout(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

    # === Git Operations ===

    def create_worktree(self, session_id: str, base_branch: str = "main") -> Path:
        """Create a git worktree for a session.

        Args:
            session_id: Session ID
            base_branch: Base branch to branch from

        Returns:
            Path to created worktree
        """
        worktree_path = self.worktrees_path / session_id
        branch_name = f"session/{session_id}"

        def _existing_worktree_for_branch(branch: str) -> Optional[Path]:
            res = run_with_timeout(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            current: Optional[Path] = None
            for line in res.stdout.splitlines():
                if line.startswith("worktree "):
                    current = Path(line.split(" ", 1)[1].strip())
                elif line.startswith("branch ") and current is not None:
                    br = line.split(" ", 1)[1].strip()
                    if br.startswith("refs/heads/"):
                        br = br[len("refs/heads/"):]
                    if br == branch:
                        return current
            return None

        existing_path = _existing_worktree_for_branch(branch_name)
        if existing_path and existing_path.exists():
            return existing_path

        # If the branch already exists (created by session/new), reuse it.
        args = ["git", "worktree", "add"]
        # Create branch only when it does not exist yet.
        exists = run_with_timeout(
            ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if worktree_path.exists():
            # Worktree already materialized; return as-is
            return worktree_path
        if exists.returncode != 0:
            args += ["-b", branch_name, str(worktree_path), base_branch]
        else:
            args += [str(worktree_path), branch_name]

        try:
            run_with_timeout(
                args,
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            # If the branch is already checked out in another worktree, reuse it.
            existing_path = _existing_worktree_for_branch(branch_name)
            if existing_path and existing_path.exists():
                return existing_path
            if worktree_path.exists():
                # Git may have created the directory before failing; reuse it.
                return worktree_path
            raise

        return worktree_path

    def commit_all(self, message: str) -> None:
        """Commit all changes in the main repo.

        Args:
            message: Commit message
        """
        run_with_timeout(
            ["git", "add", "-A"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )
        status = run_with_timeout(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if status.returncode == 0:
            return
        run_with_timeout(
            ["git", "commit", "-m", message],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

    def commit_in_worktree(self, worktree_path: Path, message: str) -> None:
        """Commit changes in a worktree.

        Args:
            worktree_path: Path to worktree
            message: Commit message
        """
        run_with_timeout(
            ["git", "add", "-A"],
            cwd=worktree_path,
            check=True,
            capture_output=True
        )
        status = run_with_timeout(
            ["git", "diff", "--cached", "--quiet"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if status.returncode == 0:
            return
        run_with_timeout(
            ["git", "commit", "-m", message],
            cwd=worktree_path,
            check=True,
            capture_output=True
        )

    def get_head_hash(self, worktree_path: Path) -> str:
        """Return HEAD commit hash for a worktree."""
        res = run_with_timeout(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return (res.stdout or "").strip()

    def get_changed_files_in_worktree(
        self,
        worktree_path: Path,
        base_branch: str = "main"
    ) -> List[str]:
        """Get list of changed files in worktree compared to base.

        Args:
            worktree_path: Path to worktree
            base_branch: Base branch to compare against

        Returns:
            List of changed file paths
        """
        result = run_with_timeout(
            ["git", "diff", "--name-only", base_branch],
            cwd=worktree_path,
            check=True,
            capture_output=True,
            text=True
        )
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]

    def create_test_file(self, path: Path, content: str) -> None:
        """Create a test file with content.

        Args:
            path: Path to file (can be in worktree)
            content: File content
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    # === Assertions ===

    def assert_worktree_exists(self, path: Path) -> None:
        """Assert worktree exists at path."""
        assert path.exists(), f"Worktree path {path} does not exist"
        assert (path / ".git").exists(), f"Worktree {path} is not a valid git directory"

    def assert_branch_exists(self, branch_name: str) -> None:
        """Assert git branch exists."""
        result = run_with_timeout(
            ["git", "branch", "--list", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        assert branch_name in result.stdout, f"Branch {branch_name} does not exist"

    def assert_files_changed(
        self,
        worktree_path: Path,
        expected_files: List[str],
        base_branch: str = "main"
    ) -> None:
        """Assert expected files were changed in worktree."""
        actual_files = self.get_changed_files_in_worktree(worktree_path, base_branch)
        for expected_file in expected_files:
            assert expected_file in actual_files, (
                f"Expected file {expected_file} not in changed files: {actual_files}"
            )
