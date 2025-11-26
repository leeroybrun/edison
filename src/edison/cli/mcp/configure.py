"""
Generic MCP configure command.

SUMMARY: Configure .mcp.json entries for all managed MCP servers
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from edison.core.mcp.config import configure_mcp_json

SUMMARY = "Configure .mcp.json for all MCP servers"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""

    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Target project path (defaults to current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show resulting configuration without writing",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        help="Override target MCP config file path",
    )
    parser.add_argument(
        "--server",
        action="append",
        dest="servers",
        help="Limit configuration to the specified MCP server id (repeatable)",
    )


def _normalize_servers(raw: Sequence[str] | None) -> list[str] | None:
    if raw is None:
        return None
    servers = [s.strip() for s in raw if s and s.strip()]
    return servers or None


def main(args: argparse.Namespace) -> int:
    """Configure .mcp.json with Edison-managed MCP server entries."""

    project_root = Path(args.project_path).expanduser().resolve()
    server_ids = _normalize_servers(args.servers)

    try:
        result = configure_mcp_json(
            project_root=project_root,
            config_file=args.config_file,
            server_ids=server_ids,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        meta = result.get("_meta", {})
        target = meta.get("path", project_root / ".mcp.json")
        print(f"✅ Configured .mcp.json at: {target}")
        return 0

    except ValueError as exc:
        print(f"Error: invalid configuration - {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive catch-all
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
