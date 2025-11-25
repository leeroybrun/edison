"""Session validation logic."""
from __future__ import annotations

import re
from typing import Any, Dict

from ..exceptions import ValidationError
from .config import SessionConfig

_CONFIG = SessionConfig()

def validate_session_id_format(session_id: str) -> bool:
    """Validate session ID format against configured regex and length."""
    regex = _CONFIG.get_id_regex()
    max_len = _CONFIG.get_max_id_length()
    
    if len(session_id) > max_len:
        raise ValidationError(f"Session ID exceeds maximum length of {max_len}")
        
    if not re.fullmatch(regex, session_id):
        raise ValidationError(f"Session ID does not match pattern: {regex}")
        
    return True

def validate_session_structure(session: Dict[str, Any]) -> bool:
    """Validate basic session structure."""
    if "state" not in session:
        raise ValidationError("Session missing required field: state")
    return True
