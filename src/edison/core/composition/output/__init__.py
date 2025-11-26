"""Output handling for composition.

Includes output path configuration, formatting utilities, header resolution,
and document generation (state machine docs, etc.).
"""
from __future__ import annotations

from .config import (
    OutputConfig,
    ClientOutputConfig,
    SyncConfig,
    OutputConfigLoader,
    get_output_config,
)
from .headers import (
    build_generated_header,
    load_header_template,
    resolve_version,
)
from .formatting import (
    format_for_zen,
    format_rules_context,
    compose_for_role,
)
from .state_machine import generate_state_machine_doc

__all__ = [
    # Config
    "OutputConfig",
    "ClientOutputConfig",
    "SyncConfig",
    "OutputConfigLoader",
    "get_output_config",
    # Headers
    "build_generated_header",
    "load_header_template",
    "resolve_version",
    # Formatting
    "format_for_zen",
    "format_rules_context",
    "compose_for_role",
    # Document generation
    "generate_state_machine_doc",
]
