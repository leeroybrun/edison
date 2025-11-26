"""Session validation logic."""
from __future__ import annotations

from typing import Any, Dict

from ..exceptions import ValidationError
from .id import validate_session_id, SessionIdError


def validate_session_id_format(session_id: str) -> bool:
    """Validate session ID format against configured regex and length.
    
    This is a wrapper around validate_session_id that returns bool
    and raises ValidationError instead of SessionIdError.
    
    Args:
        session_id: The session ID to validate
        
    Returns:
        True if validation passes
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        validate_session_id(session_id)
        return True
    except SessionIdError as e:
        raise ValidationError(str(e)) from e


def validate_session_structure(session: Dict[str, Any]) -> bool:
    """Validate basic session structure."""
    if "state" not in session:
        raise ValidationError("Session missing required field: state")
    return True
