"""Reusable web server lifecycle management.

This module is intentionally *not* QA-specific. It provides primitives for:
- Ensuring a server/stack is "correct" via verify steps
- Optionally starting/stopping the server/stack
- Cross-process locking to avoid port fights

The QA/validation layer can build on these primitives to manage servers around
validator execution.
"""

from .manager import (
    ensure_web_server,
    stop_web_server,
    web_server_lifecycle,
    web_server_lock_path,
)
from .models import (
    WebServerConfig,
    WebServerHandle,
    WebServerLockConfig,
    WebServerLockScope,
    WebServerStartConfig,
    WebServerStopConfig,
    WebServerVerifyConfig,
    WebServerVerifyStep,
)
from .resolver import resolve_web_server_config

__all__ = [
    "WebServerConfig",
    "WebServerHandle",
    "WebServerLockConfig",
    "WebServerLockScope",
    "WebServerStartConfig",
    "WebServerStopConfig",
    "WebServerVerifyConfig",
    "WebServerVerifyStep",
    "ensure_web_server",
    "stop_web_server",
    "web_server_lock_path",
    "web_server_lifecycle",
    "resolve_web_server_config",
]
