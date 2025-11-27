"""IDE-specific composition modules for Edison framework.

This package contains modules for composing IDE-specific artifacts:
- base.py: Base class for IDE composers
- commands.py: Slash commands for IDE platforms (Claude, Cursor, Codex)
- hooks.py: Lifecycle hooks for IDE platforms
- settings.py: Settings.json composition for IDE platforms

These modules are part of the composition engine and handle all IDE
integration aspects.
"""

from .base import IDEComposerBase
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
    # Base
    "IDEComposerBase",
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



