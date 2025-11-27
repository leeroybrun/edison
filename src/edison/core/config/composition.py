"""Backward-compatible re-export for CompositionConfig.

The canonical location is now edison.core.config.domains.composition.
"""
from __future__ import annotations

from .domains.composition import CompositionConfig

__all__ = ["CompositionConfig"]



