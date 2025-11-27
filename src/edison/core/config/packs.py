"""Backward-compatible re-export for PacksConfig.

The canonical location is now edison.core.config.domains.packs.
"""
from __future__ import annotations

from .domains.packs import PacksConfig

__all__ = ["PacksConfig"]



