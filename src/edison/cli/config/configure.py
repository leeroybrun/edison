"""
Edison config configure command.

SUMMARY: Interactive configuration menu
"""

from __future__ import annotations

import argparse
import sys

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
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Interactive configuration - delegates to setup module."""
    from edison.core.setup import configure_project
    from edison.core.config import ConfigManager
    from edison.core.utils.paths import resolve_project_root
    from pathlib import Path

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        config_manager = ConfigManager(repo_root)

        if args.key:
            # Direct key-value setting
            if not args.value:
                print("Error: --value required when using --key", file=sys.stderr)
                return 1

            config_manager.set(args.key, args.value)
            config_manager.save()
            print(f"Set {args.key} = {args.value}")
            return 0

        # Interactive menu
        result = configure_project(repo_root, interactive=True)

        if result.get("success"):
            print("Configuration completed successfully")
            return 0
        else:
            print(f"Configuration failed: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
