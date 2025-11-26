"""MCP (Model Context Protocol) configuration and utilities.

This module provides helpers for managing MCP server configurations
and `.mcp.json` files.
"""
from __future__ import annotations

from .config import (
    McpServerConfig,
    McpConfig,
    build_mcp_servers,
    configure_mcp_json,
)

__all__ = [
    "McpServerConfig",
    "McpConfig",
    "build_mcp_servers",
    "configure_mcp_json",
]
