"""
Edison task ready command.

SUMMARY: List tasks ready to be claimed
"""

from __future__ import annotations

import argparse

SUMMARY = "List tasks ready to be claimed"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )


def main(args: argparse.Namespace) -> int:
    """List ready tasks."""
    # TODO: Import from edison.core.task once imports are converted
    if args.json:
        import json
        print(json.dumps({"tasks": [], "status": "placeholder"}))
    else:
        print("Ready tasks: (import conversion pending)")

    return 0
