"""
Edison config configure command.

SUMMARY: Interactive configuration menu (alias for 'edison init --reconfigure')

This command provides interactive project configuration through the setup
questionnaire. It's equivalent to running 'edison init --reconfigure'.

For single key-value changes, use --key and --value flags.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_repo_root_flag, get_repo_root
from edison.core.config import ConfigManager
from edison.core.setup import configure_project, WriteMode

SUMMARY = "Interactive configuration menu"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--key",
        type=str,
        help="Specific configuration key to set (e.g., 'project.name')",
    )
    parser.add_argument(
        "--value",
        type=str,
        help="Value to set for the key (requires --key)",
    )
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Include advanced configuration questions",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config files",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing config files",
    )
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Interactive configuration - uses unified setup implementation."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        config_manager = ConfigManager(repo_root)

        # Direct key-value setting mode
        if args.key:
            if not args.value:
                formatter.error("--value required when using --key", error_code="error")
                return 1

            # Use ConfigManager's set/save methods
            config_manager.set(args.key, args.value)
            saved_path = config_manager.save()
            formatter.text(f"✅ Set {args.key} = {args.value}")
            formatter.text(f"   Written to: {saved_path.name}")
            return 0

        # Interactive questionnaire mode
        formatter.text("\n" + "="*60)
        formatter.text("  Edison Configuration")
        formatter.text("="*60 + "\n")
        
        # Determine write mode
        if args.force:
            write_mode = WriteMode.OVERWRITE
        elif args.merge:
            write_mode = WriteMode.MERGE
        else:
            write_mode = WriteMode.MERGE  # Default to merge for reconfiguration
        
        mode = "advanced" if args.advanced else "basic"
        
        formatter.text(f"📋 Running configuration questionnaire ({mode} mode)...")
        formatter.text("   Press Enter to accept defaults shown in [brackets]\n")

        result = configure_project(
            repo_root=repo_root,
            interactive=True,
            mode=mode,
            write_files=True,
            write_mode=write_mode,
            overrides_only=True,
        )

        if result.get("success"):
            # Report what was written
            write_result = result.get("write_result")
            if write_result:
                if write_result.files_written:
                    formatter.text("\n📝 Config files written:")
                    for path in write_result.files_written:
                        formatter.text(f"   - {path.name}")
                
                if write_result.files_merged:
                    formatter.text("\n🔄 Config files merged:")
                    for path in write_result.files_merged:
                        formatter.text(f"   - {path.name}")
                
                if write_result.files_skipped:
                    formatter.text("\n⏭️  Files skipped (use --force to overwrite):")
                    for path in write_result.files_skipped:
                        formatter.text(f"   - {path.name}")
            
            formatter.text("\n✅ Configuration completed successfully")
            formatter.text("   Run 'edison compose all' to apply changes")
            return 0
        else:
            error = result.get("error", "Unknown error")
            formatter.text(f"❌ Configuration failed: {error}")
            return 1

    except KeyboardInterrupt:
        formatter.text("\n\n⚠️  Configuration cancelled by user.")
        return 130
    except Exception as e:
        formatter.error(e, error_code="configure_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
