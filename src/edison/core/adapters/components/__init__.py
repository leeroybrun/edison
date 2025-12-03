"""Platform adapter components.

Components are platform-AGNOSTIC pieces that can be reused across
different platform adapters (hooks, commands, settings, etc.).

Components provide specific functionality like:
- Composing hooks from definitions
- Composing commands from definitions
- Composing settings from definitions

All components extend AdapterComponent base class.
"""
from __future__ import annotations

from .base import AdapterComponent

__all__ = ["AdapterComponent"]
