"""Pal MCP platform adapter package.

This package provides the PalAdapter platform adapter along with
supporting mixins for role-based prompt composition and discovery.
"""
from __future__ import annotations

from .adapter import PalAdapter, PalAdapterError
from .composer import PalComposerMixin, _canonical_model
from .discovery import PalDiscoveryMixin, _canonical_role
from .sync import PalSyncMixin

__all__ = [
    "PalAdapter",
    "PalAdapterError",
    "PalComposerMixin",
    "PalDiscoveryMixin",
    "PalSyncMixin",
    "_canonical_model",
    "_canonical_role",
]
