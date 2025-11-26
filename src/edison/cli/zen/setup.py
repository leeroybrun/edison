"""
Edison zen setup command.

SUMMARY: Setup zen-mcp-server for Edison integration
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from edison.core.utils.dependencies import detect_uvx, detect_zen_mcp_server

SUMMARY = "Setup zen-mcp-server for Edison integration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check setup without installing",
    )


def main(args: argparse.Namespace) -> int:
    """Setup zen-mcp-server for Edison integration."""

    # Check zen-mcp-server first
    zen_available, zen_path = detect_zen_mcp_server()

    if zen_available:
        if zen_path:
            print(f"✅ zen-mcp-server found at: {zen_path}")
        else:
            print("✅ zen-mcp-server available via uvx (will install on first use)")
        return 0

    # Check uvx
    uvx_status = detect_uvx()

    if not uvx_status.available:
        print(f"❌ {uvx_status.install_instruction}")
        if not args.check:
            return 1
        return 0

    if args.check:
        print("ℹ️  zen-mcp-server will be installed via uvx on first use")
        return 0

    # Install via uvx
    print("Installing zen-mcp-server via uvx...")
    try:
        subprocess.run([
            "uvx", "--from",
            "git+https://github.com/BeehiveInnovations/zen-mcp-server.git",
            "zen-mcp-server", "--version"
        ], check=True)
        print("✅ zen-mcp-server installed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
