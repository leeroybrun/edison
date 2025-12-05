"""
Data models for the Edison Rules system.

This module defines the core dataclasses used throughout the rules engine:
- Rule: A single enforceable rule
- RuleViolation: A record of a rule that was violated
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Rule:
    """A single enforceable rule.
    
    Attributes:
        id: Unique rule identifier
        description: Human-readable description
        enforced: Whether the rule is actively enforced
        blocking: Whether violation blocks transition
        reference: Path to guideline/doc
        config: Optional per-rule configuration payload
        title: Display title (from composition)
        content: Composed content body (from RulesRegistry)
        category: Rule category (validation, development, etc.)
        contexts: List of context types this rule applies to
        cli: CLI display configuration (commands, timing)
    """

    id: str
    description: str
    enforced: bool = True
    blocking: bool = False
    reference: Optional[str] = None  # Path to guideline/doc
    # Optional per-rule configuration payload (YAML → dict)
    # Example for validator-approval:
    #   config:
    #     requireReport: true
    #     maxAgeDays: 7
    config: Optional[Dict[str, Any]] = None
    # From composition system
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    contexts: List[str] = field(default_factory=list)
    # CLI display configuration: {commands: ["task claim"], timing: "before"}
    cli: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.blocking and not self.enforced:
            raise ValueError(f"Rule {self.id}: blocking rules must be enforced")


@dataclass
class RuleViolation:
    """A rule that was violated."""

    rule: Rule
    task_id: str
    message: str
    severity: str  # 'blocking' or 'warning'


__all__ = [
    "Rule",
    "RuleViolation",
]
