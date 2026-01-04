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
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from edison.core.utils.subprocess import run_ci_command_from_string

from .base import EngineConfig, ValidationResult
from .parsers import ensure_parsers_loaded, get_parser

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorMetadata

logger = logging.getLogger(__name__)

CanExecuteReason = Literal[
    "ok",
    "disabled_by_config",
    "binary_missing",
    "no_command",
    "config_error",
]


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

    def can_execute_details(self) -> tuple[bool, CanExecuteReason, str]:
        """Return whether the engine can execute and why.

        This is intended for operator-facing UX (avoid misleading "CLI missing"
        when execution is disabled by config).

        Returns:
            (can_execute, reason, detail)
        """
        # Config-driven safety: external CLI validators are disabled unless explicitly enabled.
        try:
            from edison.core.config.domains.qa import QAConfig

            allow = QAConfig(repo_root=self.project_root).orchestration_config.get("allowCliEngines", False)
            # Supported values:
            # - false: disable all CLI engines
            # - true: allow all CLI engines
            # - string: allow only this engine ID
            # - string[]: allow only these engine IDs (preferred)
            allowed = False
            if allow is True:
                allowed = True
            elif allow is False or allow is None:
                allowed = False
            elif isinstance(allow, str):
                allowed = allow.strip() == self.config.id
            elif isinstance(allow, list):
                allow_set = {str(v).strip() for v in allow if str(v).strip()}
                allowed = self.config.id in allow_set
            else:
                allowed = False

            if not allowed:
                return (
                    False,
                    "disabled_by_config",
                    "orchestration.allowCliEngines is false (or does not allow this engine id). "
                    "Set orchestration.allowCliEngines=true in .edison/config/orchestration.yaml to enable.",
                )
        except Exception as exc:
            return False, "config_error", f"Failed to read orchestration.allowCliEngines: {exc}"

        if not self.command:
            return False, "no_command", "Engine has no configured command"

        if shutil.which(self.command) is None:
            return False, "binary_missing", f"Command not found in PATH: {self.command}"

        return True, "ok", ""

    def can_execute(self) -> bool:
        """Check if the CLI tool is available on the system.

        Returns:
            True if command exists in PATH
        """
        can, _, _ = self.can_execute_details()
        return bool(can)

    def run(
        self,
        validator: ValidatorMetadata,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None = None,
        evidence_service: EvidenceService | None = None,
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

        try:
            prompt_input: str | None = None
            prompt_args: list[str] | None = None

            if validator.prompt:
                prompt_text = self._render_prompt_text(
                    validator=validator,
                    task_id=task_id,
                    session_id=session_id,
                    worktree_path=worktree_path,
                    round_num=round_num,
                    evidence_service=evidence_service,
                )

                # Persist the effective prompt for auditability when possible.
                prompt_path: Path | None = None
                if evidence_service:
                    try:
                        round_dir = evidence_service.ensure_round(round_num)
                        prompt_path = round_dir / f"prompt-{validator.id}.md"
                        prompt_path.write_text(prompt_text, encoding="utf-8")
                    except Exception:
                        prompt_path = None

                if self.config.prompt_mode == "stdin":
                    prompt_input = prompt_text
                    sentinel = (self.config.stdin_prompt_arg or "").strip()
                    prompt_args = [sentinel] if sentinel else None
                elif self.config.prompt_mode == "arg":
                    prompt_args = [prompt_text]
                else:
                    if prompt_path is None:
                        # Fall back to a temp file when we can't write to evidence.
                        tmp = tempfile.NamedTemporaryFile("w", suffix=f"-{validator.id}.md", delete=False)
                        try:
                            tmp.write(prompt_text)
                            prompt_path = Path(tmp.name)
                        finally:
                            tmp.close()
                    prompt_args = self._format_prompt_args(prompt_path)

            # Build the command (may raise on invalid MCP injection config).
            cmd_parts = self._build_command(validator, worktree_path, prompt_args=prompt_args)

        except Exception as exc:
            duration = time.time() - start_time
            logger.error(f"CLI validator '{validator.id}' failed during setup: {exc}", exc_info=True)
            return ValidationResult(
                validator_id=validator.id,
                verdict="blocked",
                summary=f"Validator setup failed: {exc}",
                raw_output="",
                duration=duration,
                exit_code=-1,
                error=str(exc),
            )

        env = dict(os.environ)
        # Prevent Edison/session context from leaking into validator runs (validators should be reproducible
        # from the repo state alone, not dependent on the operator's active session).
        env.pop("AGENTS_SESSION", None)
        env.pop("EDISON_SESSION_ID", None)
        env.pop("PAL_WORKING_DIR", None)

        # Make common repo-local tool shims available (uv/mypy/ruff/pytest, node tools, etc).
        try:
            venv_bin = worktree_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
        except Exception:
            pass
        try:
            node_bin = worktree_path / "node_modules" / ".bin"
            if node_bin.exists():
                env["PATH"] = f"{node_bin}{os.pathsep}{env.get('PATH', '')}"
        except Exception:
            pass

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
                env=env,
                timeout=validator.timeout,
                capture_output=True,
                text=True,
                check=False,
                input=prompt_input,
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
        validator: ValidatorMetadata,
        worktree_path: Path,
        *,
        prompt_args: list[str] | None = None,
    ) -> list[str]:
        """Build the command line from configuration.

        Args:
            validator: Validator metadata
            worktree_path: Working directory path

        Returns:
            List of command parts
        """
        cmd: list[str] = [self.command]

        # Some CLIs (e.g., Codex) require global flags before the subcommand.
        cmd.extend(self.config.pre_flags)

        required_mcp = getattr(validator, "mcp_servers", []) or []
        override_style = (self.config.mcp_override_style or "").strip()
        if override_style and required_mcp:
            from edison.core.mcp.config import build_mcp_servers
            from edison.core.mcp.injection import build_mcp_cli_overrides

            project_root = (self.project_root or worktree_path).expanduser().resolve()
            _, mcp_servers, _ = build_mcp_servers(project_root)
            cmd.extend(
                build_mcp_cli_overrides(
                    override_style,
                    mcp_servers,
                    required_servers=[str(s).strip() for s in required_mcp if str(s).strip()],
                )
            )

        # Add subcommand if configured
        if self.config.subcommand:
            cmd.append(self.config.subcommand)
            # Some CLIs use a flag-like "subcommand" (e.g. `-p`) that requires a
            # positional argument immediately after it. When prompt args are
            # available, place them directly after the dash-subcommand so we don't
            # interleave output flags between the flag and its value.
            if prompt_args is not None and str(self.config.subcommand).startswith("-"):
                cmd.extend(prompt_args)
                # Mark prompt as consumed so we don't fall back to treating
                # `validator.prompt` as a positional file argument later.
                prompt_args = []

        # Add output format flags
        cmd.extend(self.config.output_flags)

        # Add read-only flags
        cmd.extend(self.config.read_only_flags)

        if prompt_args is not None:
            cmd.extend(prompt_args)
        else:
            # Backward compatibility: treat prompt as a path argument.
            if validator.prompt:
                prompt_path = self._resolve_prompt_path(validator.prompt)
                if prompt_path:
                    cmd.append(str(prompt_path))

        return cmd

    def _format_prompt_args(self, prompt_path: Path) -> list[str]:
        flag = (self.config.prompt_flag or "").strip()
        if flag:
            return [flag, str(prompt_path)]
        return [str(prompt_path)]

    def _render_prompt_text(
        self,
        *,
        validator: ValidatorMetadata,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None,
        evidence_service: EvidenceService | None,
    ) -> str:
        prompt_path = self._resolve_prompt_path(validator.prompt)
        base = ""
        if prompt_path and prompt_path.exists():
            base = prompt_path.read_text(encoding="utf-8")

        # Keep the dynamic prelude compact and path-based (avoid embedding large logs).
        round_dir = None
        bundle_path = None
        impl_path = None
        if evidence_service:
            try:
                round_dir = evidence_service.ensure_round(round_num)
                bundle_path = round_dir / evidence_service.bundle_filename
                impl_path = round_dir / evidence_service.implementation_filename
            except Exception:
                pass

        changed_files: list[str] = []
        try:
            from edison.core.context.files import FileContextService

            ctx = FileContextService(project_root=worktree_path).get_for_task(
                task_id=task_id, session_id=session_id
            )
            changed_files = ctx.all_files or []
        except Exception:
            changed_files = []

        changed_preview = "\n".join([f"- {p}" for p in changed_files[:30]])
        if len(changed_files) > 30:
            changed_preview += f"\n- (+{len(changed_files) - 30} more)"

        prelude_lines = [
            "# Edison Validator Run (Auto)",
            "",
            "## Context",
            f"- Validator: {validator.id} ({validator.name})",
            f"- Task ID: {task_id}",
            f"- Session ID: {session_id}",
            f"- Round: {round_num if round_num is not None else 'N/A'}",
            f"- Worktree: {worktree_path}",
        ]
        try:
            raw_web = getattr(validator, "web_server", None)
            if isinstance(raw_web, dict):
                url = str(raw_web.get("url", raw_web.get("base_url", raw_web.get("baseUrl"))) or "").strip()
                if url:
                    prelude_lines.append(f"- Web Server URL: {url}")
                health = str(raw_web.get("healthcheck_url", raw_web.get("healthcheckUrl", raw_web.get("healthcheck"))) or "").strip()
                if health:
                    prelude_lines.append(f"- Web Server Probe: {health}")
        except Exception:
            pass
        if round_dir:
            prelude_lines.append(f"- Evidence Round Dir: {round_dir}")
        if bundle_path:
            prelude_lines.append(f"- Bundle Summary: {bundle_path}")
        if impl_path:
            prelude_lines.append(f"- Implementation Report: {impl_path}")

        prelude_lines.extend(
            [
                "",
                "## Changed Files (Detected)",
                changed_preview or "- (none detected)",
                "",
                "## Instructions",
                "1. Read the bundle + implementation report paths above (if they exist).",
                "2. Validate the current working tree in this worktree (use `git status --porcelain` and `git diff`).",
                "3. Focus only on changes relevant to this Task ID.",
                "4. Return a clear decision line exactly in this form:",
                "   Verdict: approve | reject | blocked",
                "5. Then provide: Summary, Findings (bullets), Strengths (bullets).",
                "",
                "---",
                "",
            ]
        )

        return "\n".join(prelude_lines) + base

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
            from edison.core.utils.paths import get_project_config_dir

            project_path = get_project_config_dir(self.project_root, create=False) / prompt
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
        evidence_service: EvidenceService,
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
        validator: ValidatorMetadata,
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
        extracted_verdict = self._extract_verdict_from_response(response)

        if exit_code != 0:
            verdict = "error"
        elif error:
            verdict = "pending"  # Parser had issues
        elif extracted_verdict is not None:
            verdict = extracted_verdict
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
        import re

        response_lower = response.lower()

        # Prefer explicit "Verdict: <x>" markers when present.
        m = re.search(r"\bverdict\s*:\s*(approve|approved|reject|rejected|blocked|pending)\b", response_lower)
        if m:
            token = m.group(1)
            if token.startswith("approve"):
                return "approve"
            if token.startswith("reject"):
                return "reject"
            if token.startswith("block"):
                return "blocked"
            if token.startswith("pend"):
                return "pending"

        # Fail-closed heuristics:
        # - Never infer "approve" from incidental language like "please approve" or "needs approval".
        # - Only infer "reject"/"blocked" when the language is unambiguously negative.
        if re.search(r"\bnot\s+approved\b", response_lower):
            return "reject"
        if re.search(r"\bunable\s+to\s+approve\b", response_lower):
            return "reject"
        if re.search(r"\bcannot\s+approve\b", response_lower):
            return "reject"
        if re.search(r"\bcan['’]t\s+approve\b", response_lower):
            return "reject"
        if re.search(r"\bcant\s+approve\b", response_lower):
            return "reject"
        if re.search(r"\bcan['’]t\s+be\s+approved\b", response_lower):
            return "reject"
        if re.search(r"\bcant\s+be\s+approved\b", response_lower):
            return "reject"

        if re.search(r"\breject(?:ed)?\b", response_lower):
            return "reject"

        if re.search(r"\bblocked\b", response_lower):
            return "blocked"

        return None


__all__ = ["CLIEngine"]
