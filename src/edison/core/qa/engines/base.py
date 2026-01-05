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
from datetime import datetime, timezone
import os
import socket
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
    pre_flags: list[str] = field(default_factory=list)
    subcommand: str = ""
    output_flags: list[str] = field(default_factory=list)
    read_only_flags: list[str] = field(default_factory=list)
    response_parser: str = "plain_text"
    description: str = ""
    prompt_mode: str = "file"  # file | arg | stdin
    prompt_flag: str = ""  # used when prompt_mode == "file"
    stdin_prompt_arg: str = "-"  # used when prompt_mode == "stdin" (when CLI needs a sentinel)
    mcp_override_style: str = ""  # optional: client-specific per-invocation MCP overrides

    @classmethod
    def from_dict(cls, engine_id: str, data: dict[str, Any]) -> EngineConfig:
        """Create EngineConfig from configuration dictionary."""
        prompt_mode = data.get("prompt_mode", data.get("promptMode", "file"))
        prompt_flag = data.get("prompt_flag", data.get("promptFlag", ""))
        stdin_prompt_arg = data.get("stdin_prompt_arg", data.get("stdinPromptArg", "-"))
        mcp_override_style = data.get("mcp_override_style", data.get("mcpOverrideStyle", ""))
        pre_flags = data.get("pre_flags", data.get("preFlags", []))
        if not isinstance(pre_flags, list):
            pre_flags = []

        return cls(
            id=engine_id,
            type=data.get("type", "cli"),
            command=data.get("command", ""),
            pre_flags=pre_flags,
            subcommand=data.get("subcommand", ""),
            output_flags=data.get("output_flags", []),
            read_only_flags=data.get("read_only_flags", []),
            response_parser=data.get("response_parser", "plain_text"),
            description=data.get("description", ""),
            prompt_mode=str(prompt_mode or "file"),
            prompt_flag=str(prompt_flag or ""),
            stdin_prompt_arg=str(stdin_prompt_arg or "-"),
            mcp_override_style=str(mcp_override_style or ""),
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
        *,
        task_id: str,
        round_num: int,
        model: str,
        pal_role: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> dict[str, Any]:
        """Convert to a validator report dict.

        Must match the canonical validator report frontmatter schema.
        """
        now = datetime.now(timezone.utc).isoformat()
        report_started = started_at or (self.tracking or {}).get("startedAt") or now
        report_completed = completed_at or (self.tracking or {}).get("completedAt") or now

        # Normalize verdict into the schema's vocabulary
        verdict = self.verdict
        if verdict == "error":
            verdict = "blocked"

        tracking: dict[str, Any] = {
            "processId": int(os.getpid()),
            "hostname": socket.gethostname(),
            "startedAt": report_started,
            "completedAt": report_completed,
        }
        last_active = (self.tracking or {}).get("lastActive")
        if last_active is not None:
            tracking["lastActive"] = last_active
        continuation_id = (self.tracking or {}).get("continuationId")
        if continuation_id is not None:
            tracking["continuationId"] = continuation_id

        report: dict[str, Any] = {
            "taskId": task_id,
            "round": int(round_num),
            "validatorId": self.validator_id,
            "model": model,
            "verdict": verdict,
            "findings": self.findings or [],
            "strengths": self.strengths or [],
            "context7Used": bool(self.context7_used),
            "context7Packages": list(self.context7_packages or []),
            "evidenceReviewed": list(self.evidence_reviewed or []),
            "summary": self.summary or "",
            "followUpTasks": list(self.follow_up_tasks or []),
            "tracking": tracking,
        }

        if pal_role is not None:
            report["palRole"] = pal_role

        return report


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
