"""
Edison zen configure command.

SUMMARY: Configure .mcp.json for zen-mcp-server integration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from edison.core.templates.mcp_config import configure_mcp_json

SUMMARY = "Configure .mcp.json for zen-mcp-server integration"


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


def main(args: argparse.Namespace) -> int:
    """Configure .mcp.json with the edison-zen MCP server entry."""

    project_root = Path(args.project_path).expanduser().resolve()

    try:
        result = configure_mcp_json(
            project_root=project_root,
            config_file=args.config_file,
            overwrite=True,
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
