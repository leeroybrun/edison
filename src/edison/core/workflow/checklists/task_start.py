"""Task start checklist engine.

This module provides a centralized checklist engine that computes what operators
should do before beginning work on a task.

Design principles:
- Single source of truth for pre-work checklists
- Reusable across `session next` and `session track start`
- Configuration-driven (severities, items, thresholds from YAML)
- Extensible to support multiple checklist kinds (task, session, qa)

Checklist Model (v1):
- id: Stable identifier for the item
- severity: blocker | warning | info
- title: Human-readable title
- rationale: Explanation of why this matters
- status: ok | missing | invalid | unknown
- evidence_paths: Paths to relevant evidence files
- suggested_commands: CLI commands to fix issues
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ChecklistItem:
    """A single checklist item with status and metadata.

    Attributes:
        id: Stable identifier for the item (e.g., 'tdd-reminder', 'evidence-round')
        severity: One of 'blocker', 'warning', 'info'
        title: Human-readable title
        rationale: Explanation of why this matters
        status: One of 'ok', 'missing', 'invalid', 'unknown'
        evidence_paths: Paths to relevant evidence files
        suggested_commands: CLI commands to fix issues
    """

    id: str
    severity: str
    title: str
    rationale: str
    status: str
    evidence_paths: list[str] = field(default_factory=list)
    suggested_commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "rationale": self.rationale,
            "status": self.status,
            "evidencePaths": list(self.evidence_paths),
            "suggestedCommands": list(self.suggested_commands),
        }


@dataclass(frozen=True, slots=True)
class ChecklistResult:
    """Result of computing a checklist for a task.

    Attributes:
        kind: The checklist kind (e.g., 'task_start', 'session_start', 'qa_start')
        task_id: Task identifier this checklist was computed for
        items: List of ChecklistItem instances
    """

    kind: str
    task_id: str
    items: list[ChecklistItem] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        """Return True if any blocker item has non-ok status."""
        return any(
            item.severity == "blocker" and item.status not in ("ok",)
            for item in self.items
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "kind": self.kind,
            "taskId": self.task_id,
            "items": [item.to_dict() for item in self.items],
            "hasBlockers": self.has_blockers,
        }


class TaskStartChecklistEngine:
    """Engine for computing task start checklists.

    This engine computes what operators should do before beginning work on a task.
    It is the single source of truth, reused by:
    - `edison session track start` output
    - `edison session next` per wip task

    V1 Checklist Items:
    - TDD reminder (info/warning)
    - Evidence round initialized (blocker if missing)
    - Implementation report present
    - Context7 required packages (missing vs invalid markers)
    """

    kind: str = "task_start"

    def compute(self, task_id: str, session_id: str | None = None) -> ChecklistResult:
        """Compute the task start checklist for a given task.

        Args:
            task_id: Task identifier
            session_id: Session identifier (used for validator roster building)

        Returns:
            ChecklistResult with all checklist items and their statuses
        """
        items: list[ChecklistItem] = []

        # 1. TDD Reminder (always present, status based on task state)
        items.append(self._build_tdd_reminder(task_id))

        # 2. Evidence Round Initialization (blocker if missing)
        items.append(self._build_evidence_round_item(task_id))

        # 3. Implementation Report
        items.append(self._build_implementation_report_item(task_id))

        # 4. Context7 Packages (if required by validators)
        ctx7_items = self._build_context7_items(task_id, session_id)
        items.extend(ctx7_items)

        return ChecklistResult(kind=self.kind, task_id=task_id, items=items)

    def _build_tdd_reminder(self, task_id: str) -> ChecklistItem:
        """Build TDD reminder checklist item."""
        return ChecklistItem(
            id="tdd-reminder",
            severity="warning",
            title="TDD Workflow Required",
            rationale="Write failing tests (RED) before implementation (GREEN), then refactor.",
            status="ok",  # Always OK - this is a reminder, not a gate
            evidence_paths=[],
            suggested_commands=[
                "Write failing test first",
                "Run tests to confirm RED phase",
                "Implement minimal code to pass",
                "Refactor with tests green",
            ],
        )

    def _build_evidence_round_item(self, task_id: str) -> ChecklistItem:
        """Build evidence round initialization checklist item."""
        from edison.core.qa.evidence import EvidenceService

        ev_svc = EvidenceService(task_id)
        current_round = ev_svc.get_current_round()

        if current_round is None:
            return ChecklistItem(
                id="evidence-round",
                severity="blocker",
                title="Evidence Round Not Initialized",
                rationale="Evidence round directory must exist before starting work.",
                status="missing",
                evidence_paths=[],
                suggested_commands=[
                    f"edison evidence init {task_id}",
                ],
            )

        round_dir = ev_svc.get_current_round_dir()
        return ChecklistItem(
            id="evidence-round",
            severity="blocker",
            title="Evidence Round Initialized",
            rationale="Evidence round directory exists and is ready for artifacts.",
            status="ok",
            evidence_paths=[str(round_dir)] if round_dir else [],
            suggested_commands=[],
        )

    def _build_implementation_report_item(self, task_id: str) -> ChecklistItem:
        """Build implementation report checklist item."""
        from edison.core.qa.evidence import EvidenceService

        ev_svc = EvidenceService(task_id)
        current_round = ev_svc.get_current_round()

        if current_round is None:
            return ChecklistItem(
                id="implementation-report",
                severity="warning",
                title="Implementation Report",
                rationale="Implementation report documents changes made in this round.",
                status="unknown",
                evidence_paths=[],
                suggested_commands=[
                    f"edison evidence init {task_id}",
                    "Create implementation-report.md with YAML frontmatter",
                ],
            )

        impl_data = ev_svc.read_implementation_report(current_round)
        round_dir = ev_svc.get_current_round_dir()
        impl_path = round_dir / ev_svc.implementation_filename if round_dir else None

        if not impl_data:
            return ChecklistItem(
                id="implementation-report",
                severity="warning",
                title="Implementation Report Missing",
                rationale="Implementation report documents changes made in this round.",
                status="missing",
                evidence_paths=[str(impl_path)] if impl_path else [],
                suggested_commands=[
                    f"Create {impl_path}" if impl_path else "Create implementation-report.md",
                ],
            )

        return ChecklistItem(
            id="implementation-report",
            severity="warning",
            title="Implementation Report Present",
            rationale="Implementation report documents changes made in this round.",
            status="ok",
            evidence_paths=[str(impl_path)] if impl_path else [],
            suggested_commands=[],
        )

    def _build_context7_items(
        self, task_id: str, session_id: str | None
    ) -> list[ChecklistItem]:
        """Build Context7 package checklist items.

        Uses the existing Context7 validation primitives from the actions module.
        """
        items: list[ChecklistItem] = []

        try:
            from edison.core.session.next.actions import build_context7_status

            ctx7_status = build_context7_status(task_id, session_id)
            required_packages = ctx7_status.get("required_packages", [])

            if not required_packages:
                # No Context7 packages required for this task
                return items

            missing_pkgs = ctx7_status.get("missing", [])
            invalid_markers = ctx7_status.get("invalid", [])
            valid_pkgs = ctx7_status.get("valid", [])
            evidence_dir = ctx7_status.get("evidence_dir")
            suggested = ctx7_status.get("suggested_commands", [])

            # Create a summary item for Context7 status
            if missing_pkgs or invalid_markers:
                # Compute status
                if missing_pkgs:
                    status = "missing"
                    title = f"Context7: {len(missing_pkgs)} package(s) missing markers"
                else:
                    status = "invalid"
                    title = f"Context7: {len(invalid_markers)} package(s) have invalid markers"

                rationale_parts = []
                if missing_pkgs:
                    rationale_parts.append(f"Missing: {', '.join(missing_pkgs)}")
                if invalid_markers:
                    invalid_desc = [
                        f"{inv['package']} (missing: {', '.join(inv.get('missing_fields', []))})"
                        for inv in invalid_markers
                    ]
                    rationale_parts.append(f"Invalid: {', '.join(invalid_desc)}")

                items.append(
                    ChecklistItem(
                        id="context7-packages",
                        severity="warning",
                        title=title,
                        rationale="; ".join(rationale_parts),
                        status=status,
                        evidence_paths=[evidence_dir] if evidence_dir else [],
                        suggested_commands=suggested,
                    )
                )
            elif valid_pkgs:
                # All required packages have valid markers
                items.append(
                    ChecklistItem(
                        id="context7-packages",
                        severity="info",
                        title=f"Context7: {len(valid_pkgs)} package(s) have valid markers",
                        rationale=f"Valid: {', '.join(valid_pkgs)}",
                        status="ok",
                        evidence_paths=[evidence_dir] if evidence_dir else [],
                        suggested_commands=[],
                    )
                )

        except Exception:
            # Fail gracefully - Context7 check is optional
            pass

        return items


__all__ = [
    "ChecklistItem",
    "ChecklistResult",
    "TaskStartChecklistEngine",
]
