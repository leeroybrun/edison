"""Platform adapter components.

Components are platform-AGNOSTIC pieces that can be reused across
different platform adapters (hooks, commands, settings, etc.).

Components provide specific functionality like hooks, commands, and settings
while reusing a shared AdapterContext provided by the platform adapter.
"""
from __future__ import annotations

from .base import AdapterComponent, AdapterContext

# Commands
from .commands import (
    CommandArg,
    CommandDefinition,
    CommandComposer,
    PlatformCommandAdapter,
    ClaudeCommandAdapter,
    CursorCommandAdapter,
    CodexCommandAdapter,
    compose_commands,
)

# Hooks
from .hooks import (
    HookComposer,
    HookDefinition,
    compose_hooks,
    ALLOWED_TYPES,
)

# Settings
from .settings import SettingsComposer

__all__ = [
    # Base
    "AdapterComponent",
    # Commands
    "CommandArg",
    "CommandDefinition",
    "CommandComposer",
    "PlatformCommandAdapter",
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
]
