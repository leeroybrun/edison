"""
Generic MCP setup command.

SUMMARY: Configure and validate MCP server entries from mcp.yml
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Sequence

from edison.core.mcp.config import build_mcp_servers, configure_mcp_json

SUMMARY = "Setup MCP servers defined in mcp.yml (no mocks, YAML-driven)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register CLI arguments."""

    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Project directory (defaults to current directory)",
    )
    parser.add_argument(
        "--server",
        action="append",
        dest="servers",
        help="Limit to specific server id (repeatable)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only validate requirements; do not attempt installation",
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


def _normalize_servers(raw: Sequence[str] | None) -> list[str] | None:
    if raw is None:
        return None
    servers = [s.strip() for s in raw if s and s.strip()]
    return servers or None


def _find_missing_commands(requirements: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for cmd in requirements:
        if not shutil.which(cmd):
            missing.append(cmd)
    return missing


def main(args: argparse.Namespace) -> int:
    """Configure .mcp.json and validate required binaries."""

    project_root = Path(args.project_path).expanduser().resolve()
    server_ids = _normalize_servers(args.servers)

    try:
        target_path, servers, setup = build_mcp_servers(project_root)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if server_ids is not None:
        servers = {sid: cfg for sid, cfg in servers.items() if sid in server_ids}
        setup = {sid: meta for sid, meta in setup.items() if sid in servers}

    if not servers:
        print("Error: No MCP servers match selection", file=sys.stderr)
        return 1

    # Validate command requirements from YAML (no hardcoded defaults)
    for server_id, meta in setup.items():
        requirements = (meta.get("require") or {}).get("commands", [])
        missing = _find_missing_commands(requirements)
        if missing:
            msg = f"❌ Missing required commands for {server_id}: {', '.join(sorted(missing))}"
            if args.check:
                print(msg)
            else:
                print(msg, file=sys.stderr)

    result = configure_mcp_json(
        project_root=project_root,
        config_file=args.config_file or target_path,
        server_ids=list(servers.keys()),
        overwrite=True,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    meta = result.get("_meta", {})
    target = meta.get("path", target_path)
    print(f"✅ Configured MCP servers at: {target}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
