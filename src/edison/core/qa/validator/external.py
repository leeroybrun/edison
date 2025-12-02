"""External validator runner for executing external CLI tools.

This module provides infrastructure for running external validation tools
(starting with CodeRabbit) and capturing their output as evidence.

Design principles:
- Config-driven: Commands and timeouts come from YAML configuration
- No mocks: Real subprocess execution using edison.core.utils.subprocess
- Evidence-first: All raw output is saved to evidence directory
- Generic framework: Supports any external CLI tool via configuration
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.config.domains.timeouts import TimeoutsConfig
from edison.core.utils.subprocess import run_ci_command_from_string
from edison.core.qa.evidence import EvidenceService

logger = logging.getLogger(__name__)


class ExternalValidatorRunner:
    """Executes external CLI validation tools and captures evidence.

    This runner provides a generic framework for executing external validation
    tools as subprocesses, with config-driven commands and timeouts.

    Example usage:
        runner = ExternalValidatorRunner(task_id="1234", session_id="abc")
        result = runner.run_coderabbit(
            worktree_path="/path/to/worktree",
            config={"command": "coderabbit review", "type": "uncommitted"}
        )

    The runner automatically:
    - Builds commands from config templates
    - Executes with appropriate timeouts
    - Saves raw output to evidence directory
    - Returns structured results with timing info
    """

    def __init__(
        self,
        task_id: str,
        session_id: str,
        project_root: Optional[Path] = None
    ) -> None:
        """Initialize external validator runner.

        Args:
            task_id: Task identifier for evidence organization
            session_id: Session identifier for evidence organization
            project_root: Optional project root path for config resolution
        """
        self.task_id = task_id
        self.session_id = session_id
        self.project_root = project_root

        # Initialize evidence service for storing raw outputs
        self.evidence_service = EvidenceService(task_id, project_root)

        # Initialize timeout config
        self.timeout_config = TimeoutsConfig(repo_root=project_root)

    def run_coderabbit(
        self,
        worktree_path: Path | str,
        config: Dict[str, Any],
        round_num: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute CodeRabbit CLI tool and capture output.

        Args:
            worktree_path: Path to git worktree to analyze
            config: Configuration dict containing:
                - command: Base command string (e.g., "coderabbit review")
                - type: Review type - "uncommitted", "committed", or "all" (optional)
                - base: Base branch for comparison (optional)
                - promptOnly: If true, add --prompt-only flag (optional)
                - timeout: Override timeout in seconds (optional)
            round_num: Optional validation round number

        Returns:
            Dict containing:
                - success: True if command executed successfully
                - stdout: Standard output from command
                - stderr: Standard error from command
                - exit_code: Process exit code
                - evidence_path: Path where raw output was saved
                - duration: Execution time in seconds

        Raises:
            ValueError: If worktree_path doesn't exist or config is invalid
            RuntimeError: If command execution fails critically
        """
        worktree = Path(worktree_path)
        if not worktree.exists():
            raise ValueError(f"Worktree path does not exist: {worktree_path}")

        # Extract config parameters
        base_cmd = config.get("command")
        if not base_cmd:
            raise ValueError("CodeRabbit config must specify 'command'")

        review_type = config.get("type", "uncommitted")
        base_branch = config.get("base")
        prompt_only = config.get("promptOnly", False)
        explicit_timeout = config.get("timeout")

        # Build command arguments
        extra_args: List[str] = []

        # Add type argument
        if review_type in ("uncommitted", "committed", "all"):
            extra_args.extend(["--type", review_type])

        # Add base branch if specified
        if base_branch:
            extra_args.extend(["--base", str(base_branch)])

        # Add working directory
        extra_args.extend(["--cwd", str(worktree)])

        # Add prompt-only flag if requested
        if prompt_only:
            extra_args.append("--prompt-only")

        logger.debug(
            f"Running CodeRabbit for task {self.task_id}: "
            f"base_cmd={base_cmd}, args={extra_args}"
        )

        # Determine timeout
        timeout = explicit_timeout if explicit_timeout is not None else self.timeout_config.default_seconds

        # Execute command
        start_time = time.time()
        try:
            result = run_ci_command_from_string(
                base_cmd,
                extra_args=extra_args,
                cwd=worktree,
                timeout=timeout,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
            duration = time.time() - start_time

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode
            success = exit_code == 0

            logger.info(
                f"CodeRabbit completed for task {self.task_id}: "
                f"exit_code={exit_code}, duration={duration:.2f}s"
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"CodeRabbit execution failed for task {self.task_id}: {e}",
                exc_info=True
            )
            stdout = ""
            stderr = str(e)
            exit_code = -1
            success = False

        # Save raw output to evidence
        evidence_path = self._save_evidence(
            validator_id="coderabbit",
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            round_num=round_num,
        )

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "evidence_path": str(evidence_path),
            "duration": duration,
        }

    def run_external(
        self,
        validator_id: str,
        command: str,
        extra_args: List[str] | None = None,
        cwd: Optional[Path | str] = None,
        timeout: Optional[float] = None,
        round_num: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generic method for running any external validator tool.

        This provides a generic interface for executing external validation
        tools with consistent evidence capture and error handling.

        Args:
            validator_id: Identifier for the validator (used in evidence filename)
            command: Base command string to execute
            extra_args: Additional arguments to append to command
            cwd: Working directory for command execution
            timeout: Timeout in seconds (uses default if None)
            round_num: Optional validation round number

        Returns:
            Dict containing:
                - success: True if command executed successfully
                - stdout: Standard output from command
                - stderr: Standard error from command
                - exit_code: Process exit code
                - evidence_path: Path where raw output was saved
                - duration: Execution time in seconds

        Raises:
            RuntimeError: If command execution fails critically
        """
        if extra_args is None:
            extra_args = []

        logger.debug(
            f"Running external validator '{validator_id}' for task {self.task_id}: "
            f"command={command}, args={extra_args}"
        )

        # Determine timeout
        effective_timeout = timeout if timeout is not None else self.timeout_config.default_seconds

        # Execute command
        start_time = time.time()
        try:
            result = run_ci_command_from_string(
                command,
                extra_args=extra_args,
                cwd=cwd,
                timeout=effective_timeout,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
            duration = time.time() - start_time

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode
            success = exit_code == 0

            logger.info(
                f"External validator '{validator_id}' completed for task {self.task_id}: "
                f"exit_code={exit_code}, duration={duration:.2f}s"
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"External validator '{validator_id}' failed for task {self.task_id}: {e}",
                exc_info=True
            )
            stdout = ""
            stderr = str(e)
            exit_code = -1
            success = False

        # Save raw output to evidence
        evidence_path = self._save_evidence(
            validator_id=validator_id,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            round_num=round_num,
        )

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "evidence_path": str(evidence_path),
            "duration": duration,
        }

    def _save_evidence(
        self,
        validator_id: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        round_num: Optional[int] = None,
    ) -> Path:
        """Save command output to evidence directory.

        Args:
            validator_id: Identifier for the validator
            stdout: Standard output to save
            stderr: Standard error to save
            exit_code: Process exit code
            round_num: Optional validation round number

        Returns:
            Path where evidence was saved
        """
        # Ensure round directory exists
        round_dir = self.evidence_service.ensure_round(round_num)

        # Determine evidence filename
        evidence_filename = f"command-{validator_id}.txt"
        evidence_path = round_dir / evidence_filename

        # Format output with metadata
        content_lines = [
            f"=== External Validator: {validator_id} ===",
            f"Task ID: {self.task_id}",
            f"Session ID: {self.session_id}",
            f"Exit Code: {exit_code}",
            "",
            "=== STDOUT ===",
            stdout,
            "",
            "=== STDERR ===",
            stderr,
            "",
        ]

        content = "\n".join(content_lines)

        # Write evidence file
        try:
            evidence_path.write_text(content, encoding="utf-8")
            logger.debug(f"Saved evidence to {evidence_path}")
        except Exception as e:
            logger.error(f"Failed to save evidence to {evidence_path}: {e}")
            raise RuntimeError(f"Failed to save evidence: {e}") from e

        return evidence_path


__all__ = [
    "ExternalValidatorRunner",
]
