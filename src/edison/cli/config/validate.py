"""
Edison config validate command.

SUMMARY: Validate project configuration
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter

SUMMARY = "Validate project configuration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation",
    )


def main(args: argparse.Namespace) -> int:
    """Validate configuration."""
    formatter = OutputFormatter(json_mode=False)

    # TODO: Import from edison.core.config once imports are converted
    mode = "strict" if args.strict else "normal"
    formatter.text(f"Validating configuration ({mode} mode)...")
    formatter.text("Configuration: placeholder (import conversion pending)")
    return 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
