"""IDE-specific composition modules for Edison framework.

This package contains modules for composing IDE-specific artifacts:
- commands.py: Slash commands for IDE platforms (Claude, Cursor, Codex)
- hooks.py: Lifecycle hooks for IDE platforms
- settings.py: Settings.json composition for IDE platforms

These were moved from edison.core.composition to maintain coherence
between composition (prompt/guideline composition) and IDE concerns.
"""

from .commands import (
    CommandArg,
    CommandDefinition,
    CommandComposer,
    PlatformAdapter,
    ClaudeCommandAdapter,
    CursorCommandAdapter,
    CodexCommandAdapter,
    compose_commands,
)
from .hooks import (
    HookComposer,
    HookDefinition,
    compose_hooks,
    ALLOWED_TYPES,
)
from .settings import (
    SettingsComposer,
    merge_permissions,
)

__all__ = [
    # Commands
    "CommandArg",
    "CommandDefinition",
    "CommandComposer",
    "PlatformAdapter",
    "ClaudeCommandAdapter",
    "CursorCommandAdapter",
    "CodexCommandAdapter",
    "compose_commands",
    # Hooks
    "HookComposer",
    "HookDefinition",
    "compose_hooks",
    "ALLOWED_TYPES",
    # Settings
    "SettingsComposer",
    "merge_permissions",
]
