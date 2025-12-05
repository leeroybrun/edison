"""
Generic MCP configure command.

SUMMARY: Configure .mcp.json entries for all managed MCP servers
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.core.mcp.config import configure_mcp_json
from edison.cli import OutputFormatter, add_dry_run_flag
from edison.cli.mcp._utils import normalize_servers

SUMMARY = "Configure .mcp.json for all MCP servers"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""

    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Target project path (defaults to current directory)",
    )
    add_dry_run_flag(parser)
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


def main(args: argparse.Namespace) -> int:
    """Configure .mcp.json with Edison-managed MCP server entries."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    project_root = Path(args.project_path).expanduser().resolve()
    server_ids = normalize_servers(args.servers)

    try:
        result = configure_mcp_json(
            project_root=project_root,
            config_file=args.config_file,
            server_ids=server_ids,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            formatter.json_output(result)
            return 0

        meta = result.get("_meta", {})
        target = meta.get("path", project_root / ".mcp.json")
        formatter.text(f"✅ Configured .mcp.json at: {target}")
        return 0

    except ValueError as exc:
        formatter.error(exc, message=f"invalid configuration - {exc}", error_code="error")
        return 1
    except Exception as exc:  # pragma: no cover - defensive catch-all
        formatter.error(exc, error_code="error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
