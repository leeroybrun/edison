"""
Edison tampering disable command.

SUMMARY: Disable tampering protection

Disables tampering protection for the Edison project by updating the
tampering configuration file.
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.config.domains import TamperingConfig

SUMMARY = "Disable tampering protection"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Execute the tampering disable command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        tampering_config = TamperingConfig(repo_root=repo_root)

        # Disable tampering protection
        tampering_config.set_enabled(False)

        # Get the config file path for output
        config_path = tampering_config._get_config_file_path()

        if formatter.json_mode:
            formatter.json_output({
                "enabled": False,
                "configPath": str(config_path),
            })
        else:
            formatter.text("Tampering protection disabled.")
            formatter.text(f"  Config: {config_path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="tampering_disable_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
