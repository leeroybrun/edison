"""Zen MCP platform adapter package.

This package provides the ZenAdapter platform adapter along with
supporting mixins for role-based prompt composition and discovery.
"""
from __future__ import annotations

from .adapter import ZenAdapter, ZenAdapterError
from .composer import ZenComposerMixin, _canonical_model
from .discovery import ZenDiscoveryMixin, _canonical_role
from .sync import ZenSyncMixin, WORKFLOW_HEADING

__all__ = [
    "ZenAdapter",
    "ZenAdapterError",
    "ZenComposerMixin",
    "ZenDiscoveryMixin",
    "ZenSyncMixin",
    "_canonical_model",
    "_canonical_role",
    "WORKFLOW_HEADING",
]
