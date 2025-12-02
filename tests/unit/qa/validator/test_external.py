"""Tests for external validator runner (CodeRabbit integration).

NO MOCKS - real files, real subprocess calls, real behavior.
Tests use simple echo commands to verify the runner's behavior.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.qa.validator.external import ExternalValidatorRunner


@pytest.fixture
def evidence_setup(tmp_path: Path):
    """Set up evidence directory structure for tests."""
    # Create project structure
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create .project/qa/validation-evidence structure
    qa_dir = project_root / ".project" / "qa" / "validation-evidence"
    qa_dir.mkdir(parents=True)

    # Create a worktree directory
    worktree = project_root / "worktree"
    worktree.mkdir()

    return {
        "project_root": project_root,
        "qa_dir": qa_dir,
        "worktree": worktree,
        "task_id": "test-task-123",
        "session_id": "test-session-abc",
    }


class TestExternalValidatorRunner:
    """Tests for ExternalValidatorRunner class."""

    def test_init_creates_runner(self, evidence_setup):
        """Verify runner initializes correctly."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        assert runner.task_id == evidence_setup["task_id"]
        assert runner.session_id == evidence_setup["session_id"]
        assert runner.evidence_service is not None

    def test_run_external_executes_command(self, evidence_setup):
        """Verify run_external executes simple commands."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        # Use echo command which works on all systems
        result = runner.run_external(
            validator_id="test-echo",
            command="echo",
            extra_args=["hello", "world"],
            cwd=evidence_setup["worktree"],
            timeout=30,
        )

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "hello world" in result["stdout"]
        assert result["duration"] > 0

    def test_run_external_saves_evidence(self, evidence_setup):
        """Verify output is saved to evidence directory."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        result = runner.run_external(
            validator_id="test-evidence",
            command="echo",
            extra_args=["test output"],
            cwd=evidence_setup["worktree"],
        )

        # Verify evidence path is returned
        assert "evidence_path" in result
        evidence_path = Path(result["evidence_path"])

        # Verify evidence file exists and contains output
        assert evidence_path.exists()
        content = evidence_path.read_text()
        assert "test output" in content
        assert "test-evidence" in content  # Validator ID in header

    def test_run_external_handles_failing_command(self, evidence_setup):
        """Verify handling of commands that return non-zero exit code."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        # Use false command which returns exit code 1
        result = runner.run_external(
            validator_id="test-fail",
            command="false",  # Returns exit code 1
            cwd=evidence_setup["worktree"],
        )

        assert result["success"] is False
        assert result["exit_code"] != 0

    def test_run_external_handles_missing_command(self, evidence_setup):
        """Verify handling of non-existent commands."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        result = runner.run_external(
            validator_id="test-missing",
            command="nonexistent-command-12345",
            cwd=evidence_setup["worktree"],
        )

        assert result["success"] is False
        assert result["exit_code"] == -1

    def test_run_external_result_structure(self, evidence_setup):
        """Verify return dict has expected structure."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        result = runner.run_external(
            validator_id="test-structure",
            command="echo",
            extra_args=["test"],
            cwd=evidence_setup["worktree"],
        )

        # Verify all required keys are present
        assert "success" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "exit_code" in result
        assert "evidence_path" in result
        assert "duration" in result

        # Verify types
        assert isinstance(result["success"], bool)
        assert isinstance(result["stdout"], str)
        assert isinstance(result["stderr"], str)
        assert isinstance(result["exit_code"], int)
        assert isinstance(result["duration"], float)


class TestCodeRabbitRunner:
    """Tests for CodeRabbit-specific functionality."""

    def test_run_coderabbit_requires_worktree(self, evidence_setup):
        """Verify run_coderabbit validates worktree path exists."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        with pytest.raises(ValueError, match="does not exist"):
            runner.run_coderabbit(
                worktree_path="/nonexistent/path",
                config={"command": "coderabbit review"},
            )

    def test_run_coderabbit_requires_command(self, evidence_setup):
        """Verify run_coderabbit requires command in config."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        with pytest.raises(ValueError, match="command"):
            runner.run_coderabbit(
                worktree_path=evidence_setup["worktree"],
                config={},  # Missing command
            )

    def test_run_coderabbit_saves_evidence_with_correct_name(self, evidence_setup):
        """Verify CodeRabbit evidence is saved as command-coderabbit.txt."""
        runner = ExternalValidatorRunner(
            task_id=evidence_setup["task_id"],
            session_id=evidence_setup["session_id"],
            project_root=evidence_setup["project_root"],
        )

        # Use echo to simulate coderabbit (since coderabbit may not be installed)
        result = runner.run_coderabbit(
            worktree_path=evidence_setup["worktree"],
            config={
                "command": "echo",  # Use echo instead of coderabbit for testing
                "type": "uncommitted",
            },
        )

        evidence_path = Path(result["evidence_path"])
        assert evidence_path.name == "command-coderabbit.txt"
