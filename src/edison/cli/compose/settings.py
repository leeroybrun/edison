"""
Edison compose settings command.

SUMMARY: Compose IDE settings files from configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    """Compose IDE settings - delegates to composition engine."""
    from edison.core.ide.settings import SettingsComposer
    from edison.core.paths import resolve_project_root
    from edison.core.config import ConfigManager

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        config_mgr = ConfigManager(repo_root=repo_root)
        config = config_mgr.load_config()

        composer = SettingsComposer(config=config, repo_root=repo_root)

        if args.dry_run:
            if args.json:
                print(json.dumps({"status": "dry-run", "repo_root": str(repo_root)}))
            else:
                print(f"[dry-run] Would compose settings from {repo_root}")
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
            print(json.dumps({
                "settings": written_files,
                "targets": targets,
            }, indent=2))
        else:
            print(f"Composed settings for {len(targets)} platform(s)")
            for path in written_files:
                print(f"  - {path}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
