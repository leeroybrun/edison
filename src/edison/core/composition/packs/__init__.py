"""Edison Pack Loader, Composer, and Auto-Activation.

Responsibilities:
- Load pack manifests from `.edison/packs/<name>/` (defaults.yaml, pack-dependencies.yaml).
- Resolve dependency order with a toposort based on `requiredPacks`.
- Compose dependencies, devDependencies, and scripts with conflict detection and
  strategies: `latest-wins` (default), `first-wins`, and `strict`.
- Namespace conflicting scripts as `<pack>:<script>` while keeping the first
  occurrence under its original name.
- Auto-activate packs based on file pattern triggers.

This module is intentionally dependency-lite and self-contained so scripts can
import it directly without extra setup.
"""
from __future__ import annotations

# Auto-activation
from .activation import auto_activate_packs, yaml

# v1 Pack Loader
from .loader import (
    load_pack,
    PackManifest,
)

from .composition import (
    compose,
    compose_from_file,
)

# Metadata
from .metadata import (
    PackMetadata,
    load_pack_metadata,
)

# Validation
from .validation import (
    ValidationIssue,
    ValidationResult,
    validate_pack,
)

# v2 Pack Engine (Registry)
from .registry import (
    PackInfo,
    DependencyResult,
    discover_packs,
    resolve_dependencies,
)

__all__ = [
    # Auto-activation
    "auto_activate_packs",
    "yaml",
    # v1 Pack Loader
    "compose",
    "compose_from_file",
    "load_pack",
    "PackManifest",
    # Metadata
    "PackMetadata",
    "load_pack_metadata",
    # Validation
    "ValidationIssue",
    "ValidationResult",
    "validate_pack",
    # v2 Pack Engine
    "PackInfo",
    "DependencyResult",
    "discover_packs",
    "resolve_dependencies",
]
