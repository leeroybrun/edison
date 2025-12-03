"""
Edison compose settings command.

SUMMARY: Compose IDE settings files from configuration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.adapters.components.settings import SettingsComposer
from edison.core.config import ConfigManager

SUMMARY = "Compose IDE settings files from configuration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--claude",
        action="store_true",
        help="Only compose Claude Code settings",
    )
    parser.add_argument(
        "--cursor",
        action="store_true",
        help="Only compose Cursor settings",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for composed settings",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose IDE settings - delegates to composition engine."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        repo_root = get_repo_root(args)
        config_mgr = ConfigManager(repo_root=repo_root)
        config = config_mgr.load_config()

        composer = SettingsComposer(config=config, repo_root=repo_root)

        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "repo_root": str(repo_root)})
            else:
                formatter.text(f"[dry-run] Would compose settings from {repo_root}")
            return 0

        # Determine which settings to compose
        targets = []
        if args.claude or (not args.claude and not args.cursor):
            targets.append("claude")
        if args.cursor or (not args.claude and not args.cursor):
            targets.append("cursor")

        # Write the settings file(s)
        written_files = []
        if "claude" in targets:
            settings_path = composer.write_settings_file()
            written_files.append(str(settings_path))

        if args.json:
            formatter.json_output({
                "settings": written_files,
                "targets": targets,
            })
        else:
            formatter.text(f"Composed settings for {len(targets)} platform(s)")
            for path in written_files:
                formatter.text(f"  - {path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="compose_settings_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
