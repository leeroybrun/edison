"""Evidence exceptions."""
from __future__ import annotations

class EvidenceError(Exception):
    """Raised when evidence operations fail.

    This includes:
    - Evidence directory not found
    - Invalid report format
    - Failed to create round directory
    - Report file not found
    """
    pass
