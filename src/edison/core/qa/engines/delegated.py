"""Delegated engine for orchestrator-based validation.

This module provides the ZenMCPEngine which generates delegation instructions
for validators that should be run by an orchestrator (human or AI) rather than
executed directly via CLI.

Used as fallback when CLI tools are not available, or for validators
that require interactive orchestration.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .base import EngineConfig, ValidationResult

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorMetadata

logger = logging.getLogger(__name__)


class ZenMCPEngine:
    """Engine that generates delegation instructions for orchestrators.

    This engine does not execute validators directly. Instead, it generates
    structured instructions that can be used by an orchestrator (human or AI)
    to perform the validation manually.

    Use cases:
    - Fallback when CLI tools are not installed
    - Validators requiring interactive review
    - Custom validation workflows
    """

    def __init__(
        self,
        config: EngineConfig,
        project_root: Path | None = None,
    ) -> None:
        """Initialize the delegated engine.

        Args:
            config: Engine configuration
            project_root: Project root path
        """
        self.config = config
        self.project_root = project_root

    def can_execute(self) -> bool:
        """Delegated engine is always available.

        Returns:
            Always True - delegation instructions can always be generated
        """
        return True

    def run(
        self,
        validator: "ValidatorMetadata",
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None = None,
        evidence_service: "EvidenceService | None" = None,
    ) -> ValidationResult:
        """Generate delegation instructions for the validator.

        Args:
            validator: Validator metadata from ValidatorRegistry
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree
            round_num: Optional validation round number
            evidence_service: Optional evidence service

        Returns:
            ValidationResult with delegation instructions
        """
        logger.info(
            f"Generating delegation instructions for validator '{validator.id}'"
        )

        # Build delegation instructions
        instructions = self._build_delegation_instructions(
            validator=validator,
            task_id=task_id,
            session_id=session_id,
            worktree_path=worktree_path,
            round_num=round_num,
        )

        # Save instructions to evidence if service provided
        if evidence_service:
            self._save_instructions(
                evidence_service=evidence_service,
                validator_id=validator.id,
                instructions=instructions,
                round_num=round_num,
            )

        return ValidationResult(
            validator_id=validator.id,
            verdict="pending",
            summary=f"Delegation required for {validator.name}",
            raw_output=instructions,
            duration=0.0,
            exit_code=0,
            error=None,
            follow_up_tasks=[
                {
                    "type": "delegation",
                    "validator": validator.id,
                    "zenRole": validator.zen_role,
                    "instructions": instructions,
                }
            ],
        )

    def _build_delegation_instructions(
        self,
        validator: "ValidatorMetadata",
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None,
    ) -> str:
        """Build human/AI-readable delegation instructions.

        Args:
            validator: Validator metadata
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Working directory
            round_num: Validation round number

        Returns:
            Formatted delegation instructions
        """
        lines = [
            f"# Validator Delegation: {validator.name}",
            "",
            "## Context",
            f"- **Validator ID**: {validator.id}",
            f"- **Task ID**: {task_id}",
            f"- **Session ID**: {session_id}",
            f"- **Round**: {round_num or 'N/A'}",
            f"- **Worktree**: {worktree_path}",
            "",
            "## Zen Role",
            f"Execute as: `{validator.zen_role}`",
            "",
        ]

        # Add prompt reference if available
        if validator.prompt:
            lines.extend([
                "## Prompt File",
                f"Use validation prompt from: `{validator.prompt}`",
                "",
            ])

        # Add focus areas if specified
        if validator.focus:
            lines.extend([
                "## Focus Areas",
                *[f"- {f}" for f in validator.focus],
                "",
            ])

        # Add Context7 requirements if any
        if validator.context7_required:
            lines.extend([
                "## Context7 Requirements",
                f"Required packages: {', '.join(validator.context7_packages)}",
                "",
            ])

        # Add instructions for the orchestrator
        lines.extend([
            "## Instructions",
            "",
            "1. Read the validator prompt file specified above",
            "2. Review the code changes in the worktree",
            "3. Apply the validation criteria to the changes",
            "4. Produce a validation report with:",
            "   - Verdict: approve / reject / blocked",
            "   - Findings: List of issues found",
            "   - Strengths: Positive aspects of the implementation",
            "   - Summary: Overall assessment",
            "",
            "## Expected Output",
            "",
            "Save the validation report to:",
            f"`validator-{validator.id}-report.md`",
            "",
        ])

        return "\n".join(lines)

    def _save_instructions(
        self,
        evidence_service: "EvidenceService",
        validator_id: str,
        instructions: str,
        round_num: int | None,
    ) -> Path:
        """Save delegation instructions to evidence.

        Args:
            evidence_service: Evidence service instance
            validator_id: Validator identifier
            instructions: Delegation instructions
            round_num: Validation round number

        Returns:
            Path where instructions were saved
        """
        round_dir = evidence_service.ensure_round(round_num)
        filename = f"delegation-{validator_id}.md"
        filepath = round_dir / filename

        try:
            filepath.write_text(instructions, encoding="utf-8")
            logger.debug(f"Saved delegation instructions to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save delegation instructions: {e}")

        return filepath


__all__ = ["ZenMCPEngine"]
