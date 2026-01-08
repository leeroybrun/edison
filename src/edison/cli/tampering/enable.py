"""
Edison tampering enable command.

SUMMARY: Enable tampering protection

Enables tampering protection for the Edison project by updating the
tampering configuration file and triggering settings re-composition.
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.config.domains import TamperingConfig

SUMMARY = "Enable tampering protection"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Execute the tampering enable command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        tampering_config = TamperingConfig(repo_root=repo_root)

        # Enable tampering protection
        tampering_config.set_enabled(True)

        # Get the config file path for output
        config_path = tampering_config._get_config_file_path()

        if formatter.json_mode:
            formatter.json_output({
                "enabled": True,
                "configPath": str(config_path),
                "mode": tampering_config.mode,
                "protectedDir": str(tampering_config.protected_dir),
            })
        else:
            formatter.text("Tampering protection enabled.")
            formatter.text(f"  Config: {config_path}")
            formatter.text(f"  Mode: {tampering_config.mode}")
            formatter.text(f"  Protected dir: {tampering_config.protected_dir}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="tampering_enable_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
