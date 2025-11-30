"""Process utilities for Edison.

This package provides process inspection utilities:
- Process tree walking for session ID inference
- Process lifecycle checks (is_process_alive)
- Owner identification for session lookup
"""
from __future__ import annotations

from .inspector import (
    HAS_PSUTIL,
    find_topmost_process,
    get_current_owner,
    infer_session_id,
    is_process_alive,
)

__all__ = [
    "HAS_PSUTIL",
    "find_topmost_process",
    "get_current_owner",
    "infer_session_id",
    "is_process_alive",
]




