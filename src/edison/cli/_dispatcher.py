"""
Auto-discovery CLI dispatcher for Edison.

Scans subfolders for commands and automatically registers them.
Adding new commands = just add a .py file to the appropriate subfolder.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable


@lru_cache(maxsize=1)
def discover_domains() -> dict[str, Path]:
    """
    Discover all CLI domain subfolders (session, task, config, etc.).

    Returns:
        Dict mapping domain name to directory path
    """
    cli_dir = Path(__file__).parent
    domains = {}
    for item in cli_dir.iterdir():
        if item.name == "commands":
            continue
        if item.is_dir() and not item.name.startswith("_"):
            # Must have at least one non-init .py file
            has_commands = any(
                f.suffix == ".py" and not f.name.startswith("_")
                for f in item.iterdir()
            )
            if has_commands:
                domains[item.name] = item
    return domains


@lru_cache(maxsize=32)
def discover_root_commands() -> dict[str, dict[str, Any]]:
    """Discover top-level commands under cli/commands (no domain prefix)."""

    cli_dir = Path(__file__).parent
    commands_dir = cli_dir / "commands"
    commands: dict[str, dict[str, Any]] = {}

    if not commands_dir.exists():
        return commands

    for item in commands_dir.glob("*.py"):
        if item.name.startswith("_"):
            continue

        cmd_name = item.stem
        try:
            module = importlib.import_module(f"edison.cli.commands.{cmd_name}")
            commands[cmd_name] = {
                "module": module,
                "summary": getattr(module, "SUMMARY", cmd_name),
                "register_args": getattr(module, "register_args", None),
                "main": getattr(module, "main", None),
            }
        except ImportError as e:
            print(f"Warning: Could not import command {cmd_name}: {e}", file=sys.stderr)
            continue

    return commands


@lru_cache(maxsize=32)
def discover_commands(domain: str) -> dict[str, dict[str, Any]]:
    """
    Discover all commands in a domain subfolder.

    Args:
        domain: Name of the domain (e.g., "session", "task")

    Returns:
        Dict mapping command name to command info dict
    """
    cli_dir = Path(__file__).parent
    domain_dir = cli_dir / domain
    commands: dict[str, dict[str, Any]] = {}

    for item in domain_dir.glob("*.py"):
        if item.name.startswith("_"):
            continue

        cmd_name = item.stem
        try:
            # Import module and get metadata
            module = importlib.import_module(f"edison.cli.{domain}.{cmd_name}")
            commands[cmd_name] = {
                "module": module,
                "summary": getattr(module, "SUMMARY", f"{domain} {cmd_name}"),
                "register_args": getattr(module, "register_args", None),
                "main": getattr(module, "main", None),
            }
        except ImportError as e:
            # Skip modules with import errors (will be caught during actual use)
            print(f"Warning: Could not import {domain}.{cmd_name}: {e}", file=sys.stderr)
            continue

    return commands


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser with auto-discovered domains and commands.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="edison",
        description="Edison Framework - AI-automated project management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )

    subparsers = parser.add_subparsers(
        dest="domain",
        title="domains",
        description="Available command domains",
        metavar="<domain>",
    )

    # Register top-level commands (no domain prefix)
    for cmd_name, cmd_info in sorted(discover_root_commands().items()):
        cmd_parser = subparsers.add_parser(
            cmd_name,
            help=cmd_info["summary"],
        )
        if cmd_info["register_args"]:
            cmd_info["register_args"](cmd_parser)
        if cmd_info["main"]:
            cmd_parser.set_defaults(_func=cmd_info["main"])

    # Auto-register domains
    for domain_name in sorted(discover_domains().keys()):
        domain_commands = discover_commands(domain_name)
        if not domain_commands:
            continue

        # Create domain parser
        domain_parser = subparsers.add_parser(
            domain_name,
            help=f"{domain_name.title()} management commands",
        )
        cmd_subparsers = domain_parser.add_subparsers(
            dest="command",
            title="commands",
            description=f"Available {domain_name} commands",
            metavar="<command>",
        )

        # Auto-register commands in domain
        for cmd_name, cmd_info in sorted(domain_commands.items()):
            cmd_parser = cmd_subparsers.add_parser(
                cmd_name,
                help=cmd_info["summary"],
            )

            # Let module register its own arguments
            if cmd_info["register_args"]:
                cmd_info["register_args"](cmd_parser)

            # Set the main function as default handler
            if cmd_info["main"]:
                cmd_parser.set_defaults(_func=cmd_info["main"])

    return parser


def _get_version() -> str:
    """Get Edison version string."""
    try:
        from edison import __version__
        return __version__
    except ImportError:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for Edison CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    # If no domain specified, show help
    if not args.domain:
        parser.print_help()
        return 0

    # If no command specified and no handler bound, show domain help
    if not getattr(args, "command", None) and not getattr(args, "_func", None):
        # Re-parse with just the domain to get its help
        domain_parser = parser._subparsers._group_actions[0].choices.get(args.domain)
        if domain_parser:
            domain_parser.print_help()
        return 0

    # Execute the command
    func: Callable[[argparse.Namespace], int] | None = getattr(args, "_func", None)
    if func:
        try:
            return func(args)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
