"""
Edison config show command.

SUMMARY: Show current configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Show current configuration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "key",
        nargs="?",
        help="Specific configuration key to show (optional)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "table"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (alias for --format=json)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Show configuration - delegates to ConfigManager."""
    from edison.core.config import ConfigManager
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        config_manager = ConfigManager(repo_root)

        config_data = config_manager.get_all()

        # Handle specific key
        if args.key:
            value = config_manager.get(args.key)
            if args.json:
                print(json.dumps({args.key: value}, indent=2))
            else:
                print(f"{args.key}: {value}")
            return 0

        # Handle full config display
        output_format = "json" if args.json else args.format

        if output_format == "json":
            print(json.dumps(config_data, indent=2))
        elif output_format == "yaml":
            try:
                import yaml
                print(yaml.dump(config_data, default_flow_style=False))
            except ImportError:
                print("PyYAML not installed, falling back to JSON")
                print(json.dumps(config_data, indent=2))
        else:  # table format
            print("Configuration:")
            print("-" * 60)
            for key, value in config_data.items():
                if isinstance(value, dict):
                    print(f"{key}:")
                    for sub_key, sub_value in value.items():
                        print(f"  {sub_key}: {sub_value}")
                else:
                    print(f"{key}: {value}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
