"""Composition reporting dataclasses.

Provides structured reports for composition operations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class CompositionReport:
    """Report from a composition operation.

    Contains all information about what was processed:
    - Source layers used
    - Files included
    - Sections extracted
    - Variables resolved
    - Conditionals evaluated
    - Warnings and errors
    """

    # Identification
    entity_name: str
    entity_type: str  # "agent", "guideline", etc.
    timestamp: datetime = field(default_factory=datetime.now)

    # Source tracking
    source_layers: List[str] = field(default_factory=list)
    template_path: Optional[Path] = None

    # Processing stats
    includes_resolved: Set[str] = field(default_factory=set)
    sections_extracted: Set[str] = field(default_factory=set)
    variables_substituted: Set[str] = field(default_factory=set)
    variables_missing: Set[str] = field(default_factory=set)
    conditionals_evaluated: int = 0
    loops_expanded: int = 0

    # Warnings and errors
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def source_layer_string(self) -> str:
        """Format source layers as 'core + pack1 + pack2 + project'."""
        return " + ".join(self.source_layers) if self.source_layers else "core"

    @property
    def has_issues(self) -> bool:
        """Check if there are any warnings or errors."""
        return bool(self.warnings or self.errors or self.variables_missing)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "timestamp": self.timestamp.isoformat(),
            "source_layers": self.source_layers,
            "template_path": str(self.template_path) if self.template_path else None,
            "includes_resolved": list(self.includes_resolved),
            "sections_extracted": list(self.sections_extracted),
            "variables_substituted": list(self.variables_substituted),
            "variables_missing": list(self.variables_missing),
            "conditionals_evaluated": self.conditionals_evaluated,
            "loops_expanded": self.loops_expanded,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Composition Report: {self.entity_type}/{self.entity_name}",
            f"  Layers: {self.source_layer_string}",
            f"  Includes: {len(self.includes_resolved)}",
            f"  Sections: {len(self.sections_extracted)}",
            f"  Variables: {len(self.variables_substituted)} resolved, {len(self.variables_missing)} missing",
            f"  Conditionals: {self.conditionals_evaluated}",
        ]

        if self.warnings:
            lines.append(f"  Warnings: {len(self.warnings)}")
            for w in self.warnings[:3]:  # Show first 3
                lines.append(f"    - {w}")

        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for e in self.errors[:3]:  # Show first 3
                lines.append(f"    - {e}")

        return "\n".join(lines)


@dataclass
class BatchCompositionReport:
    """Report from composing multiple entities."""

    entity_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    reports: List[CompositionReport] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Total entities composed."""
        return len(self.reports)

    @property
    def success_count(self) -> int:
        """Entities composed without errors."""
        return sum(1 for r in self.reports if not r.errors)

    @property
    def warning_count(self) -> int:
        """Entities with warnings."""
        return sum(1 for r in self.reports if r.warnings)

    @property
    def error_count(self) -> int:
        """Entities with errors."""
        return sum(1 for r in self.reports if r.errors)

    def add_report(self, report: CompositionReport) -> None:
        """Add an individual report."""
        self.reports.append(report)

    def summary(self) -> str:
        """Generate batch summary."""
        lines = [
            f"Batch Composition Report: {self.entity_type}",
            f"  Total: {self.total_count}",
            f"  Success: {self.success_count}",
            f"  Warnings: {self.warning_count}",
            f"  Errors: {self.error_count}",
        ]

        # List entities with issues
        issues = [r for r in self.reports if r.has_issues]
        if issues:
            lines.append("  Issues:")
            for r in issues[:5]:  # Show first 5
                status = "ERROR" if r.errors else "WARN"
                lines.append(f"    [{status}] {r.entity_name}")

        return "\n".join(lines)
