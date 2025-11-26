"""Session next package - compute next actions for a session.

This package provides deterministic next action computation for session orchestration.

Public API:
    compute_next: Main function to compute recommended next actions
"""
from __future__ import annotations

from edison.core.session.next.compute import compute_next, main
from edison.core.session.next.utils import all_task_files as _all_task_files

__all__ = ["compute_next", "main", "_all_task_files"]
