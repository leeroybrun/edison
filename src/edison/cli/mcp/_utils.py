"""Shared utilities for MCP CLI commands."""
from __future__ import annotations

from typing import Sequence


def normalize_servers(raw: Sequence[str] | None) -> list[str] | None:
    """Normalize server list by stripping whitespace and filtering empty values.
    
    Args:
        raw: Raw sequence of server names, possibly with whitespace
        
    Returns:
        Normalized list of server names, or None if input is None or empty
    """
    if raw is None:
        return None
    servers = [s.strip() for s in raw if s and s.strip()]
    return servers or None


__all__ = ["normalize_servers"]

