"""
Edison compose commands command.

SUMMARY: Compose CLI commands from configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Compose CLI commands - delegates to composition engine."""
    from edison.core.composition.ide.commands import CommandComposer
    from edison.core.utils.paths import resolve_project_root
    from edison.core.config import ConfigManager

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        config_mgr = ConfigManager(repo_root=repo_root)
        config = config_mgr.load_config()

        composer = CommandComposer(config=config, repo_root=repo_root)

        # Handle --list flag
        if args.list:
            definitions = composer.load_definitions()
            if args.json:
                print(json.dumps({
                    "commands": [{"id": d.id, "command": d.command, "domain": d.domain}
                                 for d in definitions]
                }, indent=2))
            else:
                for d in definitions:
                    print(f"{d.id} ({d.domain}/{d.command})")
            return 0

        if args.dry_run:
            if args.json:
                print(json.dumps({"status": "dry-run", "repo_root": str(repo_root)}))
            else:
                print(f"[dry-run] Would compose commands from {repo_root}")
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
            print(json.dumps({
                "platforms": all_results,
                "count": sum(len(cmds) for cmds in all_results.values()),
            }, indent=2))
        else:
            for platform, commands in all_results.items():
                print(f"\n{platform}:")
                for cmd_id in commands:
                    print(f"  - {cmd_id}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
