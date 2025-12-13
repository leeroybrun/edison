"""Base classes and dataclasses for the validator engine system.

This module defines the core abstractions for the unified validator engine system:
- ValidationResult: Standard result from any validator engine
- EngineConfig: Configuration for an execution engine
- EngineProtocol: Protocol defining the engine interface

NOTE: Validator metadata is now defined in core/registries/validators.py
as ValidatorMetadata. That is THE single source of truth for validator data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorMetadata


@dataclass
class EngineConfig:
    """Configuration for a validator execution engine.

    Engines are the execution backends that run validators (CLI tools, delegation, etc.).
    """

    id: str
    type: str  # "cli" | "delegated"
    command: str = ""
    subcommand: str = ""
    output_flags: list[str] = field(default_factory=list)
    read_only_flags: list[str] = field(default_factory=list)
    response_parser: str = "plain_text"
    description: str = ""

    @classmethod
    def from_dict(cls, engine_id: str, data: dict[str, Any]) -> EngineConfig:
        """Create EngineConfig from configuration dictionary."""
        return cls(
            id=engine_id,
            type=data.get("type", "cli"),
            command=data.get("command", ""),
            subcommand=data.get("subcommand", ""),
            output_flags=data.get("output_flags", []),
            read_only_flags=data.get("read_only_flags", []),
            response_parser=data.get("response_parser", "plain_text"),
            description=data.get("description", ""),
        )


@dataclass
class ValidationResult:
    """Standard result from any validator engine.

    This dataclass normalizes output from all engines (CLI, delegated, etc.)
    into a consistent format that integrates with the evidence system.
    """

    validator_id: str
    verdict: str  # "approve" | "reject" | "blocked" | "pending" | "error"
    findings: list[dict[str, Any]] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    summary: str = ""
    follow_up_tasks: list[dict[str, Any]] = field(default_factory=list)
    context7_used: bool = False
    context7_packages: list[str] = field(default_factory=list)
    evidence_reviewed: list[str] = field(default_factory=list)
    tracking: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    raw_output: str = ""
    duration: float = 0.0
    exit_code: int = 0
    error: str | None = None

    def to_report(
        self,
        task_id: str,
        round_num: int,
        model: str = "",
    ) -> dict[str, Any]:
        """Convert to report format matching validator-report.schema.json.

        Args:
            task_id: The task identifier
            round_num: Validation round number
            model: Model name used for validation

        Returns:
            Dict matching the validator report schema
        """
        return {
            "taskId": task_id,
            "round": round_num,
            "validatorId": self.validator_id,
            "model": model,
            "zenRole": f"validator-{self.validator_id}",
            "verdict": self.verdict,
            "findings": self.findings,
            "strengths": self.strengths,
            "context7Used": self.context7_used,
            "context7Packages": self.context7_packages,
            "evidenceReviewed": self.evidence_reviewed,
            "summary": self.summary,
            "followUpTasks": self.follow_up_tasks,
            "tracking": self.tracking or {
                "processId": f"{self.validator_id}-{round_num}",
                "startedAt": datetime.now().isoformat(),
                "completedAt": datetime.now().isoformat(),
                "duration": self.duration,
            },
            "scores": self.scores,
        }


class EngineProtocol(Protocol):
    """Protocol defining the interface for validator engines.

    All engines (CLI, delegated, etc.) must implement this interface.
    """

    def can_execute(self) -> bool:
        """Check if this engine can execute (e.g., CLI tool is available).

        Returns:
            True if engine is ready to execute validators
        """
        ...

    def run(
        self,
        validator: "ValidatorMetadata",
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None = None,
        evidence_service: "EvidenceService | None" = None,
    ) -> ValidationResult:
        """Execute a validator and return results.

        Args:
            validator: Validator metadata from ValidatorRegistry
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree
            round_num: Optional validation round number
            evidence_service: Optional evidence service for saving output

        Returns:
            ValidationResult with verdict and findings
        """
        ...


__all__ = [
    "EngineConfig",
    "EngineProtocol",
    "ValidationResult",
]

