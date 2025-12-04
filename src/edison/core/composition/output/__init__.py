"""Output handling for composition.

Includes formatting utilities and header resolution.

Note: Output configuration is now handled by CompositionConfig in
edison.core.config.domains.composition.

Note: Document generation (state machine, rosters) has been moved to
composition/generators/ module.
"""
from __future__ import annotations

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
    # Headers
    "build_generated_header",
    "load_header_template",
    "resolve_version",
    # Formatting
    "format_for_zen",
    "format_rules_context",
    "compose_for_role",
]
