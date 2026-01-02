"""Checklist engines for Edison workflow orchestration.

This package provides centralized checklist computation for various workflow stages:
- task_start: Checklist for operators before beginning work on a task
- (future) session_start: Checklist for starting a new session
- (future) qa_start: Checklist for starting QA validation

The checklist model provides:
- id: Stable identifier for the item
- severity: blocker | warning | info
- title: Human-readable title
- rationale: Explanation of why this matters
- status: ok | missing | invalid | unknown
- evidence_paths: Paths to relevant evidence files
- suggested_commands: CLI commands to fix issues
"""

from __future__ import annotations

from edison.core.workflow.checklists.task_start import (
    ChecklistItem,
    ChecklistResult,
    TaskStartChecklistEngine,
)

__all__ = [
    "ChecklistItem",
    "ChecklistResult",
    "TaskStartChecklistEngine",
]

