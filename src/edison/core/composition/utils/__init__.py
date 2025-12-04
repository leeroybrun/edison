"""Composition utilities module.

Provides shared utilities for the composition system:
- Path resolution and placeholder substitution
"""
from __future__ import annotations

from .paths import resolve_project_dir_placeholders

__all__ = [
    "resolve_project_dir_placeholders",
]
