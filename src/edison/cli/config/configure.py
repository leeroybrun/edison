"""
Edison config configure command.

SUMMARY: Interactive configuration menu
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_repo_root_flag, get_repo_root
from edison.core.setup import configure_project
from edison.core.config import ConfigManager
from pathlib import Path

SUMMARY = "Interactive configuration menu"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--key",
        type=str,
        help="Specific configuration key to set (skips menu)",
    )
    parser.add_argument(
        "--value",
        type=str,
        help="Value to set for the key (requires --key)",
    )
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Interactive configuration - delegates to setup module."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        repo_root = get_repo_root(args)
        config_manager = ConfigManager(repo_root)

        if args.key:
            # Direct key-value setting
            if not args.value:
                formatter.error("--value required when using --key", error_code="error")
                return 1

            config_manager.set(args.key, args.value)
            config_manager.save()
            formatter.text(f"Set {args.key} = {args.value}")
            return 0

        # Interactive menu
        result = configure_project(repo_root, interactive=True)

        if result.get("success"):
            formatter.text("Configuration completed successfully")
            return 0
        else:
            formatter.text(f"Configuration failed: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        formatter.error(e, error_code="configure_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
