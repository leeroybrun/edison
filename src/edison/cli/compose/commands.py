"""
Edison compose commands command.

SUMMARY: Compose CLI commands from configuration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.adapters.components.commands import CommandComposer
from edison.core.config import ConfigManager

SUMMARY = "Compose CLI commands from configuration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available command definitions",
    )
    parser.add_argument(
        "--platform",
        type=str,
        help="Target platform (claude, cursor, codex)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for composed commands",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose CLI commands - delegates to composition engine."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        repo_root = get_repo_root(args)
        config_mgr = ConfigManager(repo_root=repo_root)
        config = config_mgr.load_config()

        composer = CommandComposer(config=config, repo_root=repo_root)

        # Handle --list flag
        if args.list:
            definitions = composer.load_definitions()
            if args.json:
                formatter.json_output({
                    "commands": [{"id": d.id, "command": d.command, "domain": d.domain}
                                 for d in definitions]
                })
            else:
                for d in definitions:
                    formatter.text(f"{d.id} ({d.domain}/{d.command})")
            return 0

        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "repo_root": str(repo_root)})
            else:
                formatter.text(f"[dry-run] Would compose commands from {repo_root}")
            return 0

        # Compose commands for platform(s)
        definitions = composer.filter_definitions(composer.load_definitions())

        if args.platform:
            platforms = [args.platform]
        else:
            platforms = composer._platforms()

        all_results = {}
        for platform in platforms:
            results = composer.compose_for_platform(platform, definitions)
            all_results[platform] = {cmd_id: str(path) for cmd_id, path in results.items()}

        if args.json:
            formatter.json_output({
                "platforms": all_results,
                "count": sum(len(cmds) for cmds in all_results.values()),
            })
        else:
            for platform, commands in all_results.items():
                formatter.text(f"\n{platform}:")
                for cmd_id in commands:
                    formatter.text(f"  - {cmd_id}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="compose_commands_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
