"""Context utilities for Edison framework.

This module provides services for understanding the runtime context:
- FileContext: Container for file change information
- FileContextService: Single source for modified file detection

Example:
    from edison.core.context import FileContextService

    svc = FileContextService()
    ctx = svc.get_for_task("T001")
    print(f"Modified files: {ctx.all_files}")
"""
from __future__ import annotations

from .files import FileContext, FileContextService

__all__ = ["FileContext", "FileContextService"]
