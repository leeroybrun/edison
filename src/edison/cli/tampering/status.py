"""
Edison tampering status command.

SUMMARY: Show tampering protection status

Shows the current tampering protection configuration status.
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.config.domains import TamperingConfig

SUMMARY = "Show tampering protection status"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Execute the tampering status command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        tampering_config = TamperingConfig(repo_root=repo_root)

        status = tampering_config.get_status()

        if formatter.json_mode:
            formatter.json_output(status)
        else:
            formatter.text("Tampering protection status:")
            formatter.text(f"  Enabled: {status['enabled']}")
            formatter.text(f"  Mode: {status['mode']}")
            formatter.text(f"  Protected dir: {status['protectedDir']}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="tampering_status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
