"""Compatibility task package mirroring legacy ``lib.tasks`` surface.

This package forwards to the modern ``lib.task`` implementation while
providing a small OO facade used by the current test suite.
"""
from __future__ import annotations

from .manager import TaskManager
from . import state

__all__ = ["TaskManager", "state"]

