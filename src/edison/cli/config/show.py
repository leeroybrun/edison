"""
Edison config show command.

SUMMARY: Show current configuration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

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
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Show configuration - delegates to ConfigManager."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.config import ConfigManager
    
    try:
        repo_root = get_repo_root(args)
        config_manager = ConfigManager(repo_root)

        config_data = config_manager.get_all()

        # Handle specific key
        if args.key:
            value = config_manager.get(args.key)
            if args.json:
                formatter.json_output({args.key: value})
            else:
                formatter.text(f"{args.key}: {value}")
            return 0

        # Handle full config display
        output_format = "json" if args.json else args.format

        if output_format == "json":
            formatter.json_output(config_data)
        elif output_format == "yaml":
            try:
                import yaml
                formatter.text(yaml.dump(config_data, default_flow_style=False))
            except ImportError:
                formatter.text("PyYAML not installed, falling back to JSON")
                formatter.json_output(config_data)
        else:  # table format
            formatter.text("Configuration:")
            formatter.text("-" * 60)
            for key, value in config_data.items():
                if isinstance(value, dict):
                    formatter.text(f"{key}:")
                    for sub_key, sub_value in value.items():
                        formatter.text(f"  {sub_key}: {sub_value}")
                else:
                    formatter.text(f"{key}: {value}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="config_show_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
