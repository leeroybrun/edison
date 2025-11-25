"""Test environment helpers for E2E workflow tests.

Provides isolated test environments with:
- TestProjectDir: Manages isolated .project/ directory
- TestGitRepo: Manages isolated git repository with worktree support
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from edison.core.utils.subprocess import run_with_timeout


class TestProjectDir:
    """Isolated .project directory with helper methods for testing."""

    def __init__(self, tmp_path: Path, repo_root: Path):
        """Initialize test project directory.

        Args:
            tmp_path: pytest tmp_path fixture (temporary directory)
            repo_root: Path to actual repository root (for copying configs)
        """
        self.tmp_path = tmp_path
        self.repo_root = repo_root
        self.project_root = tmp_path / ".project"
        self.agents_root = tmp_path / ".agents"

        # Setup directory structure
        self._setup_directories()
        self._setup_configs()

    def _setup_directories(self) -> None:
        """Create .project and .agents directory structure."""
        # .project structure
        (self.project_root / "tasks" / "todo").mkdir(parents=True)
        (self.project_root / "tasks" / "wip").mkdir(parents=True)
        (self.project_root / "tasks" / "done").mkdir(parents=True)
        (self.project_root / "tasks" / "validated").mkdir(parents=True)
        (self.project_root / "tasks" / "blocked").mkdir(parents=True)

        (self.project_root / "qa" / "todo").mkdir(parents=True)
        (self.project_root / "qa" / "wip").mkdir(parents=True)
        (self.project_root / "qa" / "done").mkdir(parents=True)
        (self.project_root / "qa" / "waiting").mkdir(parents=True)
        (self.project_root / "qa" / "validation-evidence").mkdir(parents=True)

        (self.project_root / "sessions" / "wip").mkdir(parents=True)
        (self.project_root / "sessions" / "done").mkdir(parents=True)
        (self.project_root / "sessions" / "validated").mkdir(parents=True)

        # .agents structure
        (self.agents_root / "sessions").mkdir(parents=True)
        (self.agents_root / "rules").mkdir(parents=True)
        (self.agents_root / "scripts").mkdir(parents=True)
        (self.agents_root / "scripts" / "lib").mkdir(parents=True)

    def _setup_configs(self) -> None:
        """Copy/create necessary config files."""
        # Copy manifest.json (required for worktree config and postTrainingPackages)
        src_manifest = self.repo_root / ".agents" / "manifest.json"
        if src_manifest.exists():
            dst_manifest = self.agents_root / "manifest.json"
            shutil.copy(src_manifest, dst_manifest)

        # Copy project .agents/config.yml (legacy) and modular overlays so
        # ConfigManager in tests sees the same configuration as the real project.
        src_config = self.repo_root / ".agents" / "config.yml"
        if src_config.exists():
            shutil.copy(src_config, self.agents_root / "config.yml")

        src_config_dir = self.repo_root / ".agents" / "config"
        if src_config_dir.exists():
            shutil.copytree(src_config_dir, self.agents_root / "config", dirs_exist_ok=True)

        # Copy validators config (required for postTrainingPackages detection)
        src_validators = self.repo_root / ".agents" / "validators" / "config.json"
        if src_validators.exists():
            validators_dir = self.agents_root / "validators"
            validators_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_validators, validators_dir / "config.json")

        # Copy session workflow config if it exists
        src_workflow = self.repo_root / ".agents" / "session-workflow.json"
        if src_workflow.exists():
            dst_workflow = self.agents_root / "session-workflow.json"
            shutil.copy(src_workflow, dst_workflow)
        else:
            # Create minimal workflow config
            workflow = {
                "initial": "session-init",
                "states": {
                    "session-init": {"type": "initial"},
                    "session-active": {"type": "normal"},
                    "session-complete": {"type": "final"}
                }
            }
            (self.agents_root / "session-workflow.json").write_text(
                json.dumps(workflow, indent=2)
            )

        # Copy task template if exists
        src_template = self.repo_root / ".project" / "tasks" / "TEMPLATE.md"
        if src_template.exists():
            shutil.copy(src_template, self.project_root / "tasks" / "TEMPLATE.md")

        # Copy QA template if exists
        src_qa_template = self.repo_root / ".project" / "qa" / "TEMPLATE.md"
        if src_qa_template.exists():
            shutil.copy(src_qa_template, self.project_root / "qa" / "TEMPLATE.md")

        # Copy session template if exists
        src_session_template = self.repo_root / ".agents" / "sessions" / "TEMPLATE.json"
        if src_session_template.exists():
            shutil.copy(src_session_template, self.agents_root / "sessions" / "TEMPLATE.json")

        # Copy lib directory (required for CLI scripts to import sessionlib, task)
        src_lib = self.repo_root / ".agents" / "scripts" / "lib"
        if src_lib.exists():
            dst_lib = self.agents_root / "scripts" / "lib"
            shutil.copytree(src_lib, dst_lib, dirs_exist_ok=True)

        # Copy task scripts directory (ensure-followups is called by tasks/ready)
        src_tasks = self.repo_root / ".agents" / "scripts" / "tasks"
        if src_tasks.exists():
            dst_tasks = self.agents_root / "scripts" / "tasks"
            dst_tasks.mkdir(parents=True, exist_ok=True)
            # Copy all task scripts
            for script_file in src_tasks.glob("*"):
                if script_file.is_file():
                    shutil.copy(script_file, dst_tasks / script_file.name)

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
        for state_dir in ["todo", "wip", "done", "validated", "blocked"]:
            task_path = self.project_root / "tasks" / state_dir / f"{task_id}.md"
            if task_path.exists():
                return task_path
        return None

    def get_task_state(self, task_id: str) -> Optional[str]:
        """Get current state of a task.

        Args:
            task_id: Task ID

        Returns:
            State name (todo/wip/done/validated/blocked) or None if not found
        """
        task_path = self.get_task_path(task_id)
        if task_path:
            return task_path.parent.name
        return None

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
        metadata = {"id": task_id, "state": self.get_task_state(task_id)}

        # Extract key fields from markdown
        for line in content.split("\n"):
            if line.startswith("- **Owner:**"):
                metadata["owner"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Wave:**"):
                metadata["wave"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Status:**"):
                metadata["status"] = line.split(":", 1)[1].strip()

        return metadata

    def get_qa_path(self, qa_id: str) -> Optional[Path]:
        """Find QA file by ID across all state directories."""
        for state_dir in ["todo", "wip", "done", "waiting"]:
            qa_path = self.project_root / "qa" / state_dir / f"{qa_id}-qa.md"
            if qa_path.exists():
                return qa_path
        return None

    def get_qa_state(self, qa_id: str) -> Optional[str]:
        """Get current state of a QA file."""
        qa_path = self.get_qa_path(qa_id)
        if qa_path:
            return qa_path.parent.name
        return None

    def get_qa_json(self, qa_id: str) -> Optional[Dict[str, Any]]:
        """Parse QA file as structured data."""
        qa_path = self.get_qa_path(qa_id)
        if not qa_path:
            return None

        content = qa_path.read_text()
        metadata = {"id": qa_id, "state": self.get_qa_state(qa_id)}

        # Extract validators if present
        if "## Validators" in content:
            validators_section = content.split("## Validators")[1].split("##")[0]
            metadata["validators"] = []
            for line in validators_section.split("\n"):
                if line.strip().startswith("- "):
                    metadata["validators"].append(line.strip()[2:])

        return metadata

    def get_session_path(self, session_id: str) -> Optional[Path]:
        """Find session file by ID."""
        for state_dir in ["wip", "done", "validated"]:
            # Check both .project/sessions and .agents/sessions
            for base in [self.project_root, self.agents_root]:
                session_path = base / "sessions" / state_dir / f"{session_id}.json"
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
        evidence_dir = (
            self.project_root / "qa" / "validation-evidence" /
            task_id / f"round-{round_num}"
        )
        evidence_file = evidence_dir / filename
        assert evidence_file.exists(), (
            f"Evidence file {filename} not found in {evidence_dir}"
        )

    # === Test Data Creation ===

    def create_task(
        self,
        task_id: str,
        wave: str = "wave1",
        slug: str = "test-task",
        state: str = "todo",
        owner: Optional[str] = None,
        primary_files: Optional[List[str]] = None,
        **kwargs
    ) -> Path:
        """Create a task file with metadata.

        DEPRECATED: This method creates mock data instead of using real CLI.
        Use run_script("tasks/new", args) from command_runner.py instead.

        Args:
            task_id: Task ID (e.g., "150-wave1-auth")
            wave: Wave identifier
            slug: Short kebab-case name
            state: Initial state (todo/wip/done/validated)
            owner: Owner session ID
            primary_files: List of primary files changed
            **kwargs: Additional metadata

        Returns:
            Path to created task file
        """
        task_dir = self.project_root / "tasks" / state
        task_path = task_dir / f"{task_id}.md"

        # Build task content
        content = f"""# Task: {task_id}

## Metadata
- **ID:** {task_id}
- **Wave:** {wave}
- **Slug:** {slug}
- **Status:** {state}
"""
        if owner:
            content += f"- **Owner:** {owner}\n"

        if primary_files:
            content += "\n## Primary Files\n"
            for file in primary_files:
                content += f"- `{file}`\n"

        content += "\n## Description\nTest task for E2E testing.\n"

        # Add any additional metadata
        for key, value in kwargs.items():
            content += f"\n## {key.replace('_', ' ').title()}\n{value}\n"

        task_path.write_text(content)
        return task_path

    def create_session(
        self,
        session_id: str,
        state: str = "wip",
        with_worktree: bool = False,
        worktree_path: Optional[Path] = None,
        **kwargs
    ) -> Path:
        """Create a session JSON file.

        DEPRECATED: This method creates mock data instead of using real CLI.
        Use run_script("session", args) from command_runner.py instead.

        Args:
            session_id: Session ID
            state: Initial state (wip/done/validated)
            with_worktree: Whether to include worktree metadata
            worktree_path: Path to worktree (if with_worktree=True)
            **kwargs: Additional session metadata

        Returns:
            Path to created session file
        """
        # Real sessions go in .project/sessions/, not .agents/sessions/
        session_dir = self.project_root / "sessions" / state
        session_dir.mkdir(parents=True, exist_ok=True)
        session_path = session_dir / f"{session_id}.json"

        # Build session data
        session_data = {
            "sessionId": session_id,
            "state": state,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "tasks": [],
            "qa": [],
            **kwargs
        }

        if with_worktree:
            if worktree_path is None:
                worktree_path = self.tmp_path / ".worktrees" / session_id
            session_data["git"] = {
                "worktreePath": str(worktree_path),
                "branch": f"session/{session_id}",
                "baseBranch": "main"
            }

        session_path.write_text(json.dumps(session_data, indent=2))
        return session_path

    def create_mock_evidence(
        self,
        task_id: str,
        round_num: int = 1,
        evidence_files: Optional[List[str]] = None
    ) -> Path:
        """Create mock evidence files for a task.

        DEPRECATED: This method creates mock data instead of using real CLI.
        Real evidence should be created by running actual validation commands.

        Args:
            task_id: Task ID
            round_num: Round number
            evidence_files: List of evidence filenames to create

        Returns:
            Path to evidence directory
        """
        if evidence_files is None:
            evidence_files = [
                "command-type-check.txt",
                "command-lint.txt",
                "command-test.txt",
                "command-build.txt"
            ]

        evidence_dir = (
            self.project_root / "qa" / "validation-evidence" /
            task_id / f"round-{round_num}"
        )
        evidence_dir.mkdir(parents=True, exist_ok=True)

        for filename in evidence_files:
            evidence_file = evidence_dir / filename
            evidence_file.write_text(f"Mock evidence for {filename}\nExit code: 0\n")

        return evidence_dir

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
        evidence_dir = (
            self.project_root / "qa" / "validation-evidence" /
            task_id / f"round-{round_num}"
        )
        evidence_dir.mkdir(parents=True, exist_ok=True)

        marker_file = evidence_dir / f"context7-{package}.txt"
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
    .project/sessions/wip/{session_id}/tasks/{task_id}/evidence/tdd/round-1
    """
    evidence_dir = (
        project.project_root
        / "sessions"
        / "wip"
        / session_id
        / "tasks"
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

    def __init__(self, tmp_path: Path):
        """Initialize test git repository.

        Args:
            tmp_path: pytest tmp_path fixture (temporary directory)
        """
        self.repo_path = tmp_path
        self.worktrees_path = tmp_path / ".worktrees"
        self.worktrees_path.mkdir(exist_ok=True)

        # Initialize git repo
        self._init_repo()

    def _init_repo(self) -> None:
        """Initialize git repository with main branch."""
        run_with_timeout(
            ["git", "init", "-b", "main"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
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
