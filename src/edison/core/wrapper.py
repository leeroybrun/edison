"""Legacy wrapper module for backward compatibility.

This module re-exports subprocess utilities from their new location.
New code should import directly from edison.core.utils.subprocess.
"""
from __future__ import annotations

from .utils.subprocess import (
    run_with_timeout,
    configured_timeout,
    check_output_with_timeout,
    reset_subprocess_timeout_cache,
)

__all__ = [
    "run_with_timeout",
    "configured_timeout",
    "check_output_with_timeout",
    "reset_subprocess_timeout_cache",
]
