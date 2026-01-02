"""Stable error types for the paths subsystem.

This module intentionally contains only exception classes so that tests that
reload other path/config modules do not accidentally create multiple distinct
exception class objects (which can break `pytest.raises` matching).
"""

from __future__ import annotations


class EdisonPathError(ValueError):
    """Raised when path resolution fails."""

    pass


__all__ = ["EdisonPathError"]

