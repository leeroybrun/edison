"""Session persistence layer."""
from __future__ import annotations

from .repository import SessionRepository
from .database import (
    create_session_database,
    drop_session_database,
)
from .archive import archive_session
from .graph import (
    register_task,
    register_qa,
    link_tasks,
    gather_cluster,
    build_validation_bundle,
    create_merge_task,
)

__all__ = [
    # Repository
    "SessionRepository",
    # Database
    "create_session_database",
    "drop_session_database",
    # Archive
    "archive_session",
    # Graph
    "register_task",
    "register_qa",
    "link_tasks",
    "gather_cluster",
    "build_validation_bundle",
    "create_merge_task",
]
