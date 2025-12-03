"""Output handling for composition.

Includes output path configuration, formatting utilities, and header resolution.

Note: Document generation (state machine, rosters) has been moved to
composition/generators/ module.
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
]
