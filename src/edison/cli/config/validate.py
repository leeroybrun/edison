"""
Edison config validate command.

SUMMARY: Validate project configuration
"""

from __future__ import annotations

import argparse

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
    # TODO: Import from edison.core.config once imports are converted
    mode = "strict" if args.strict else "normal"
    print(f"Validating configuration ({mode} mode)...")
    print("Configuration: placeholder (import conversion pending)")
    return 0
