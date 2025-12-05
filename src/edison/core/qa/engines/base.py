"""Base classes and dataclasses for the validator engine system.

This module defines the core abstractions for the unified validator engine system:
- ValidationResult: Standard result from any validator engine
- ValidatorConfig: Configuration for a single validator
- EngineConfig: Configuration for an execution engine
- EngineProtocol: Protocol defining the engine interface
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService


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
class ValidatorConfig:
    """Configuration for a single validator.

    Validators use engines to perform validation. This config defines
    which engine to use, the prompt, and execution parameters.
    """

    id: str
    name: str
    engine: str  # Engine ID to use
    prompt: str = ""  # Path to prompt file
    wave: str = ""  # Wave this validator belongs to
    fallback_engine: str | None = None  # Fallback if primary unavailable
    always_run: bool = False
    blocking: bool = True
    timeout: int = 300
    context7_required: bool = False
    context7_packages: list[str] = field(default_factory=list)
    command_args: list[str] = field(default_factory=list)
    zen_role_override: str | None = None  # Optional override for inferred zenRole
    triggers: list[str] = field(default_factory=list)
    focus: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, validator_id: str, data: dict[str, Any]) -> ValidatorConfig:
        """Create ValidatorConfig from configuration dictionary."""
        return cls(
            id=validator_id,
            name=data.get("name", validator_id),
            engine=data.get("engine", ""),
            prompt=data.get("prompt", data.get("specFile", "")),
            wave=data.get("wave", ""),
            fallback_engine=data.get("fallback_engine"),
            always_run=data.get("always_run", data.get("alwaysRun", False)),
            blocking=data.get("blocking", data.get("blocksOnFail", True)),
            timeout=data.get("timeout", 300),
            context7_required=data.get("context7_required", data.get("context7Required", False)),
            context7_packages=data.get("context7_packages", data.get("context7Packages", [])),
            command_args=data.get("command_args", data.get("commandArgs", [])),
            zen_role_override=data.get("zen_role_override"),
            triggers=data.get("triggers", []),
            focus=data.get("focus", []),
        )

    @property
    def zen_role(self) -> str:
        """Get the zenRole for this validator (inferred or overridden)."""
        if self.zen_role_override:
            return self.zen_role_override
        return f"validator-{self.id}"


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
        config: ValidatorConfig,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None = None,
        evidence_service: "EvidenceService | None" = None,
    ) -> ValidationResult:
        """Execute a validator and return results.

        Args:
            config: Validator configuration
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
    "ValidatorConfig",
]

