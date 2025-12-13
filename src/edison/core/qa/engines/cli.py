"""CLI Engine for executing external validator tools.

This module provides a single CLIEngine class that handles all CLI-based validators.
The engine is config-driven and uses pluggable parsers for output processing.

Design principles:
- Single class handles ALL CLI tools (Codex, Claude, Gemini, Auggie, CodeRabbit)
- Common logic: subprocess execution, timeout, evidence saving
- Pluggable parsing: Uses parser registry for tool-specific output processing
- Config-driven: Commands and flags come from YAML configuration
"""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from edison.core.utils.subprocess import run_ci_command_from_string

from .base import EngineConfig, ValidationResult
from .parsers import ensure_parsers_loaded, get_parser

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorMetadata

logger = logging.getLogger(__name__)


class CLIEngine:
    """Config-driven CLI engine for validator execution.

    This single class handles ALL CLI-based validators by:
    1. Building commands from configuration
    2. Executing via subprocess with timeout
    3. Parsing output using pluggable parsers
    4. Normalizing to ValidationResult
    5. Saving evidence to the appropriate round

    Example:
        engine_config = EngineConfig.from_dict("codex-cli", {
            "type": "cli",
            "command": "codex",
            "subcommand": "exec",
            "output_flags": ["--output-schema"],
            "response_parser": "codex",
        })
        engine = CLIEngine(engine_config)

        if engine.can_execute():
            result = engine.run(validator_config, task_id, session_id, worktree_path)
    """

    def __init__(
        self,
        config: EngineConfig,
        project_root: Path | None = None,
    ) -> None:
        """Initialize CLI engine with configuration.

        Args:
            config: Engine configuration
            project_root: Project root for parser loading
        """
        self.config = config
        self.project_root = project_root

        # Ensure parsers are loaded
        ensure_parsers_loaded(project_root)

    @property
    def command(self) -> str:
        """Get the base command."""
        return self.config.command

    @property
    def parser_name(self) -> str:
        """Get the parser name to use."""
        return self.config.response_parser or "plain_text"

    def can_execute(self) -> bool:
        """Check if the CLI tool is available on the system.

        Returns:
            True if command exists in PATH
        """
        if not self.command:
            return False
        return shutil.which(self.command) is not None

    def run(
        self,
        validator: "ValidatorMetadata",
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None = None,
        evidence_service: "EvidenceService | None" = None,
    ) -> ValidationResult:
        """Execute the validator CLI and return results.

        Args:
            validator: Validator metadata from ValidatorRegistry
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree to analyze
            round_num: Optional validation round number
            evidence_service: Optional evidence service for saving output

        Returns:
            ValidationResult with verdict and findings
        """
        start_time = time.time()

        # Build the command
        cmd_parts = self._build_command(validator, worktree_path)

        logger.info(
            f"Running CLI validator '{validator.id}' with command: {self.command}"
        )
        logger.debug(f"Full command: {' '.join(cmd_parts[:5])}...")

        try:
            # Execute subprocess
            result = run_ci_command_from_string(
                cmd_parts[0],
                extra_args=cmd_parts[1:],
                cwd=worktree_path,
                timeout=validator.timeout,
                capture_output=True,
                text=True,
                check=False,
            )

            duration = time.time() - start_time
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode

            logger.info(
                f"CLI validator '{validator.id}' completed: "
                f"exit_code={exit_code}, duration={duration:.2f}s"
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"CLI validator '{validator.id}' failed: {e}", exc_info=True)

            return ValidationResult(
                validator_id=validator.id,
                verdict="error",
                summary=f"CLI execution failed: {e}",
                raw_output="",
                duration=duration,
                exit_code=-1,
                error=str(e),
            )

        # Parse output
        parsed = self._parse_output(stdout)

        # Save evidence if service provided
        if evidence_service:
            self._save_evidence(
                evidence_service=evidence_service,
                validator_id=validator.id,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                round_num=round_num,
            )

        # Build result
        return self._to_validation_result(
            validator=validator,
            parsed=parsed,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration=duration,
        )

    def _build_command(
        self,
        validator: "ValidatorMetadata",
        worktree_path: Path,
    ) -> list[str]:
        """Build the command line from configuration.

        Args:
            validator: Validator metadata
            worktree_path: Working directory path

        Returns:
            List of command parts
        """
        cmd: list[str] = [self.command]

        # Add subcommand if configured
        if self.config.subcommand:
            cmd.append(self.config.subcommand)

        # Add output format flags
        cmd.extend(self.config.output_flags)

        # Add read-only flags
        cmd.extend(self.config.read_only_flags)

        # Add prompt file if specified
        if validator.prompt:
            # Resolve prompt path relative to project
            prompt_path = self._resolve_prompt_path(validator.prompt)
            if prompt_path:
                cmd.append(str(prompt_path))

        return cmd

    def _resolve_prompt_path(self, prompt: str) -> Path | None:
        """Resolve prompt file path.

        Args:
            prompt: Prompt path (may be relative to project)

        Returns:
            Resolved path or None if not found
        """
        if not prompt:
            return None

        # Try as absolute path first
        prompt_path = Path(prompt)
        if prompt_path.is_absolute() and prompt_path.exists():
            return prompt_path

        # Try relative to project root
        if self.project_root:
            project_path = self.project_root / ".edison" / prompt
            if project_path.exists():
                return project_path

            # Also try without .edison prefix
            direct_path = self.project_root / prompt
            if direct_path.exists():
                return direct_path

        return None

    def _parse_output(self, stdout: str) -> dict[str, Any]:
        """Parse CLI output using the configured parser.

        Args:
            stdout: Raw CLI stdout

        Returns:
            Parsed output dict
        """
        parser = get_parser(self.parser_name)

        if not parser:
            logger.warning(
                f"Parser '{self.parser_name}' not found, using plain_text"
            )
            parser = get_parser("plain_text")

        if parser:
            result = parser(stdout)
            return dict(result)

        # Ultimate fallback
        return {"response": stdout, "error": None, "metadata": None}

    def _save_evidence(
        self,
        evidence_service: "EvidenceService",
        validator_id: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        round_num: int | None,
    ) -> Path:
        """Save command output to evidence directory.

        Args:
            evidence_service: Evidence service instance
            validator_id: Validator identifier
            stdout: Command stdout
            stderr: Command stderr
            exit_code: Process exit code
            round_num: Validation round number

        Returns:
            Path where evidence was saved
        """
        round_dir = evidence_service.ensure_round(round_num)
        evidence_filename = f"command-{validator_id}.txt"
        evidence_path = round_dir / evidence_filename

        content_lines = [
            f"=== CLI Validator: {validator_id} ===",
            f"Engine: {self.config.id}",
            f"Command: {self.command}",
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

        try:
            evidence_path.write_text(content, encoding="utf-8")
            logger.debug(f"Saved evidence to {evidence_path}")
        except Exception as e:
            logger.error(f"Failed to save evidence: {e}")

        return evidence_path

    def _to_validation_result(
        self,
        validator: "ValidatorMetadata",
        parsed: dict[str, Any],
        stdout: str,
        stderr: str,
        exit_code: int,
        duration: float,
    ) -> ValidationResult:
        """Convert parsed output to ValidationResult.

        Args:
            validator: Validator metadata
            parsed: Parsed output from parser
            stdout: Raw stdout
            stderr: Raw stderr
            exit_code: Process exit code
            duration: Execution duration

        Returns:
            Normalized ValidationResult
        """
        # Determine verdict from exit code and response
        response = parsed.get("response", "")
        error = parsed.get("error")

        if exit_code != 0:
            verdict = "error"
        elif error:
            verdict = "pending"  # Parser had issues
        elif self._extract_verdict_from_response(response):
            verdict = self._extract_verdict_from_response(response)
        else:
            verdict = "pending"  # Need manual review

        return ValidationResult(
            validator_id=validator.id,
            verdict=verdict,
            summary=response[:500] if response else f"Exit code: {exit_code}",
            raw_output=stdout,
            duration=duration,
            exit_code=exit_code,
            error=error or (stderr if exit_code != 0 else None),
            context7_used=validator.context7_required,
            context7_packages=validator.context7_packages,
        )

    def _extract_verdict_from_response(self, response: str) -> str | None:
        """Try to extract verdict from response text.

        Looks for common patterns like "APPROVED", "REJECTED", etc.

        Args:
            response: Response text

        Returns:
            Verdict string or None if not found
        """
        response_lower = response.lower()

        # Check for explicit verdict indicators
        if "approved" in response_lower or "approve" in response_lower:
            if "not approved" in response_lower or "cannot approve" in response_lower:
                return "reject"
            return "approve"

        if "rejected" in response_lower or "reject" in response_lower:
            return "reject"

        if "blocked" in response_lower or "blocking" in response_lower:
            return "blocked"

        return None


__all__ = ["CLIEngine"]

