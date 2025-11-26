#!/usr/bin/env python3
from __future__ import annotations

"""Core composition routines for agents, validators, and guidelines.

This package provides the composition engine and related utilities for assembling
prompts, guidelines, and orchestrator manifests from core templates, pack contexts,
and project overlays.
"""

# Base types
from .base import ComposeResult

# Prompt composition
from .prompt import compose_prompt

# Zen formatting
from .zen import (
    compose_zen_prompt,
    compose_agent_zen_prompt,
    compose_validator_zen_prompt,
)

# Guideline composition
from .guideline import compose_guidelines

# Composition engine
from .engine import CompositionEngine

# Re-export utilities from includes module for backward compatibility
from ..includes import (
    ComposeError,
    resolve_includes,
    validate_composition,
    get_cache_dir,
    MAX_DEPTH,
    _repo_root,
)

# Re-export utilities from utils for backward compatibility
from ...utils.text import (
    ENGINE_VERSION,
    dry_duplicate_report,
    render_conditional_includes,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)

# Re-export pack utilities for backward compatibility
from ..packs import auto_activate_packs


__all__ = [
    # Base types
    "ComposeResult",
    # Errors
    "ComposeError",
    # Prompt composition
    "compose_prompt",
    # Guideline composition
    "compose_guidelines",
    # Zen formatting
    "compose_zen_prompt",
    "compose_agent_zen_prompt",
    "compose_validator_zen_prompt",
    # Utilities
    "resolve_includes",
    "render_conditional_includes",
    "auto_activate_packs",
    "validate_composition",
    "dry_duplicate_report",
    "ENGINE_VERSION",
    "MAX_DEPTH",
    # Engine
    "CompositionEngine",
    # Cache
    "get_cache_dir",
    # Internal utilities (exposed for testing/advanced use)
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    "_repo_root",
]
