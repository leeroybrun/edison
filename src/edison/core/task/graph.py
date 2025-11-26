"""Task metadata graph helpers (JSON-backed records)."""
from __future__ import annotations

from typing import Any, Dict

from .io import create_task_record, load_task_record, set_task_result, update_task_record

__all__ = [
    "create_task_record",
    "load_task_record",
    "update_task_record",
    "set_task_result",
]
