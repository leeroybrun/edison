#!/usr/bin/env python3
from __future__ import annotations

"""Base types for composition."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ComposeResult:
    """Result of a composition operation."""

    text: str
    dependencies: List[Path]
    cache_path: Optional[Path]
    hash: str
    duplicate_report: Optional[Dict]


__all__ = [
    "ComposeResult",
]




