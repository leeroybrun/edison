"""Edison vendor CLI commands.

Provides CLI interface for vendor management:
- list: List configured vendors
- show: Show details for a vendor
- sync: Sync vendor checkouts
- update: Update vendors to latest
- gc: Garbage collect unused caches
"""
from __future__ import annotations

SUBCOMMANDS = {
    "list": "edison.cli.vendor.list",
    "show": "edison.cli.vendor.show",
    "sync": "edison.cli.vendor.sync",
    "update": "edison.cli.vendor.update",
    "gc": "edison.cli.vendor.gc",
}

__all__ = ["SUBCOMMANDS"]
