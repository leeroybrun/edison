"""Task domain package.

This module provides the core task management functionality through:
- TaskRepository: Entity-based task persistence
- Task models: Task entity definitions
- TaskManager: High-level task management operations
- TaskQAWorkflow: Task-QA workflow orchestration

Note: TaskConfig has been moved to edison.core.config.domains.TaskConfig
"""

import getpass
import os
from typing import Callable, Optional, Tuple

from .manager import TaskManager
from .models import Task
from .repository import TaskRepository
from .workflow import TaskQAWorkflow
from .paths import safe_relative

# Compatibility layer for legacy task record API
from .compat import (
    create_task_record,
    load_task_record,
    update_task_record,
    set_task_result,
)

# State validation function
from edison.core.state.transitions import validate_transition as validate_state_transition


def default_owner(
    process_finder: Optional[Callable[[], Tuple[str, int]]] = None
) -> str:
    """Determine the default owner for tasks.

    Resolution order:
    1. Process detection via process_finder (returns process name)
    2. AGENTS_OWNER environment variable
    3. Current username via getpass.getuser()

    Args:
        process_finder: Optional callable that returns (process_name, pid).
                       Defaults to inspector.find_topmost_process.

    Returns:
        Owner string
    """
    # Try process detection first
    if process_finder is None:
        from edison.core.utils.process import inspector
        process_finder = inspector.find_topmost_process

    try:
        process_name, _pid = process_finder()
        return process_name
    except Exception:
        pass

    # Fall back to environment variable
    env_owner = os.environ.get("AGENTS_OWNER")
    if env_owner:
        return env_owner

    # Final fallback to username
    return getpass.getuser()


def normalize_record_id(record_type: str, record_id: str) -> str:
    """Normalize a record ID by removing file extensions.

    Args:
        record_type: Type of record ('task' or 'qa')
        record_id: Record identifier, possibly with .md extension

    Returns:
        Normalized record ID without extension
    """
    # Remove .md extension if present
    if record_id.endswith('.md'):
        return record_id[:-3]
    return record_id


__all__ = [
    "Task",
    "TaskRepository",
    "TaskManager",
    "TaskQAWorkflow",
    "normalize_record_id",
    "default_owner",
    "safe_relative",
    # Compatibility layer functions
    "create_task_record",
    "load_task_record",
    "update_task_record",
    "set_task_result",
    # State validation
    "validate_state_transition",
]
