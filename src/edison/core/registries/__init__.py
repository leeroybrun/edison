"""Entity registries for Edison.

This module provides read-only registries for entity metadata lookup.
Unlike repositories (CRUD), registries only provide read operations.

Architecture:
    BaseEntityManager (from entity.manager)
    └── BaseRegistry (this package)
        ├── AgentRegistry - Agent metadata from frontmatter
        └── ValidatorRegistry - Validator roster from config

These registries are separate from ComposableRegistry (in composition.registries),
which handles markdown file composition. Entity registries provide metadata lookup.
"""
from __future__ import annotations

from ._base import BaseRegistry
from .agents import AgentRegistry, AgentMetadata
from .validators import ValidatorRegistry, ValidatorMetadata

__all__ = [
    "BaseRegistry",
    "AgentRegistry",
    "AgentMetadata",
    "ValidatorRegistry",
    "ValidatorMetadata",
]
