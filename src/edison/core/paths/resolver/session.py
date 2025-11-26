"""Session ID detection logic."""
from __future__ import annotations

import os
import re
from typing import Optional

from edison.core.file_io.utils import read_json_safe
from edison.core.paths.management import get_management_paths
from edison.core.paths.resolver.base import EdisonPathError
from edison.core.paths.resolver.project import resolve_project_root


def _validate_session_id(session_id: str) -> str:
    """Validate session ID format.

    Session IDs must:
    - Be non-empty
    - Contain only alphanumeric, dash, and underscore characters
    - Not contain path traversal sequences
    - Be 64 characters or less

    Args:
        session_id: Session ID to validate

    Returns:
        str: Validated session ID

    Raises:
        EdisonPathError: If session ID is invalid
    """
    if not session_id:
        raise EdisonPathError("Session ID cannot be empty")

    if len(session_id) > 64:
        raise EdisonPathError(
            f"Session ID too long: {len(session_id)} characters (max 64)"
        )

    # Check for path traversal
    if ".." in session_id or "/" in session_id or "\\" in session_id:
        raise EdisonPathError(
            f"Session ID contains path traversal or separators: {session_id}"
        )

    # Check for valid characters (alphanumeric, dash, underscore)
    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        raise EdisonPathError(
            f"Session ID contains invalid characters: {session_id}. "
            "Only alphanumeric, dash, and underscore allowed."
        )

    return session_id


def detect_session_id(
    explicit: Optional[str] = None,
    owner: Optional[str] = None,
) -> Optional[str]:
    """Canonical session ID detection with validation.

    Detection priority:
    1. Explicit session ID parameter (if provided)
    2. project_SESSION environment variable (canonical)
    3. Auto-detect from owner / project_OWNER

    Auto-detection from owner looks for sessions in
    ``.project/sessions/active/`` whose ``session.json`` contains
    a matching ``owner`` field.

    Args:
        explicit: Explicit session ID if provided by caller
        owner: Owner name for auto-detection

    Returns:
        str: Normalized session ID, or None if cannot detect

    Raises:
        EdisonPathError: If session ID format is invalid
    """
    # Priority 1: Explicit parameter
    if explicit:
        return _validate_session_id(explicit)

    # Priority 2: project_SESSION environment variable (canonical)
    project_session = os.environ.get("project_SESSION")
    if project_session:
        return _validate_session_id(project_session)

    # Priority 3: Auto-detect from owner / project_OWNER
    if owner is None:
        owner = os.environ.get("project_OWNER")

    if owner:
        try:
            root = resolve_project_root()
            mgmt_paths = get_management_paths(root)
            sessions_active = mgmt_paths.get_session_state_dir("active")

            if not sessions_active.exists():
                return None

            # Look for session directories with matching owner
            for session_dir in sessions_active.iterdir():
                if not session_dir.is_dir():
                    continue

                session_json = session_dir / "session.json"
                if not session_json.exists():
                    continue

                try:
                    data = read_json_safe(session_json, default={})
                    if isinstance(data, dict) and data.get("owner") == owner:
                        return _validate_session_id(session_dir.name)
                except Exception:
                    continue
        except EdisonPathError:
            pass

    return None
