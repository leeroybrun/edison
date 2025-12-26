"""
Edison compose hooks command.

SUMMARY: Compose Claude Code hooks from configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.adapters.components.hooks import HookComposer
from edison.cli.compose._context import build_compose_context
from edison.core.utils.io import read_json, write_json_atomic, ensure_directory

SUMMARY = "Compose Claude Code hooks from configuration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install hooks to .git/hooks after composing",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for composed hooks",
    )
    parser.add_argument(
        "--no-settings",
        action="store_true",
        help="Skip updating settings.json with hooks configuration",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose Claude Code hooks - generates scripts and updates settings.json."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "repo_root": str(repo_root)})
            else:
                formatter.text(f"[dry-run] Would compose hooks from {repo_root}")
            return 0

        ctx = build_compose_context(repo_root=repo_root)
        hook_composer = HookComposer(ctx)

        output_dir_override: Path | None = None
        if args.output:
            output_dir_override = Path(str(args.output)).expanduser()

        hook_files = hook_composer.compose_hooks(output_dir_override=output_dir_override)

        # Update settings.json with hooks section (unless --no-settings)
        settings_updated = False
        if not args.no_settings and hook_files:
            settings_path = repo_root / ".claude" / "settings.json"
            ensure_directory(settings_path.parent)

            # Load existing settings or start fresh
            existing_settings = read_json(settings_path, default={}) if settings_path.exists() else {}

            # Generate hooks section for settings.json
            hooks_section = hook_composer.generate_settings_json_hooks_section(
                output_dir_override=output_dir_override
            )
            if hooks_section:
                existing_settings["hooks"] = hooks_section
                write_json_atomic(settings_path, existing_settings, indent=2)
                settings_updated = True

        # Install to .git/hooks if requested
        if args.install:
            git_hooks_dir = repo_root / ".git" / "hooks"
            if git_hooks_dir.exists():
                if not args.json:
                    formatter.text(f"Installed hooks to {git_hooks_dir}")
            else:
                if not args.json:
                    formatter.text(f"Warning: {git_hooks_dir} does not exist, skipping install")

        if args.json:
            formatter.json_output({
                "hooks": list(hook_files.keys()),
                "count": len(hook_files),
                "installed": args.install,
                "settings_updated": settings_updated,
            })
        else:
            formatter.text(f"Composed {len(hook_files)} hook(s):")
            for hook_id, path in hook_files.items():
                formatter.text(f"  - {hook_id}: {path.name}")
            if settings_updated:
                formatter.text(f"Updated .claude/settings.json with hooks configuration")

        return 0

    except Exception as e:
        formatter.error(e, error_code="compose_hooks_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
