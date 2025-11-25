"""Composition package exposing include resolution and composition engines."""

from .includes import (
    ComposeError,
    resolve_includes,
    get_cache_dir,
    validate_composition,
    MAX_DEPTH,
    _repo_root,
)
from .composers import (
    ComposeResult,
    compose_prompt,
    compose_guidelines,
    CompositionEngine,
)
from .commands import (  # noqa: F401
    CommandArg,
    CommandDefinition,
    CommandComposer,
    PlatformAdapter,
    ClaudeCommandAdapter,
    CursorCommandAdapter,
    CodexCommandAdapter,
)
from .hooks import HookComposer, HookDefinition  # noqa: F401
from .settings import SettingsComposer, merge_permissions  # noqa: F401
from .packs import auto_activate_packs
from ..composition_utils import (
    dry_duplicate_report,
    render_conditional_includes,
    ENGINE_VERSION,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)

__all__ = [
    "ComposeError",
    "ComposeResult",
    "compose_prompt",
    "compose_guidelines",
    "resolve_includes",
    "render_conditional_includes",
    "auto_activate_packs",
    "validate_composition",
    "dry_duplicate_report",
    "ENGINE_VERSION",
    "MAX_DEPTH",
    "get_cache_dir",
    "CompositionEngine",
    "_repo_root",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    "CommandArg",
    "CommandDefinition",
    "CommandComposer",
    "PlatformAdapter",
    "ClaudeCommandAdapter",
    "CursorCommandAdapter",
    "CodexCommandAdapter",
    "SettingsComposer",
    "HookComposer",
    "HookDefinition",
    "merge_permissions",
]
