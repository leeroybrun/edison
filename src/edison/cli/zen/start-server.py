"""
Edison zen start-server command.

SUMMARY: Start the zen-mcp-server
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SUMMARY = "Start the zen-mcp-server"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run server in background",
    )


def _run_command(cmd: list[str], background: bool) -> None:
    """Run a command either in background or foreground."""
    if background:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.run(cmd, check=True)


def _get_script_path() -> Path:
    """Get the path to run-server.sh script."""
    # Allow override via environment for testing
    script_path_str = os.environ.get("ZEN_RUN_SERVER_SCRIPT")

    if script_path_str:
        return Path(script_path_str)

    # Default location: scripts/zen/run-server.sh from project root
    # This file is at: src/edison/cli/zen/start_server.py
    # Go up 5 levels to project root
    return Path(__file__).parent.parent.parent.parent.parent / "scripts" / "zen" / "run-server.sh"


def main(args: argparse.Namespace) -> int:
    """Start the zen-mcp-server."""

    script_path = _get_script_path()

    if script_path.exists():
        # Use the run-server.sh script
        cmd = ["bash", str(script_path)]
        _run_command(cmd, args.background)
        return 0

    # Fallback to uvx
    cmd = [
        "uvx", "--from",
        "git+https://github.com/BeehiveInnovations/zen-mcp-server.git",
        "zen-mcp-server"
    ]

    try:
        _run_command(cmd, args.background)
        return 0
    except FileNotFoundError:
        print("❌ uvx not found and run-server.sh script not available.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please install zen-mcp-server or install uvx:", file=sys.stderr)
        print("  pip install uv", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
