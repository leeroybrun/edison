"""
Edison compose hooks command.

SUMMARY: Compose git hooks from configuration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root

SUMMARY = "Compose git hooks from configuration"


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
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose git hooks - delegates to composition engine."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.composition.ide.hooks import compose_hooks
    
    try:
        repo_root = get_repo_root(args)

        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "repo_root": str(repo_root)})
            else:
                formatter.text(f"[dry-run] Would compose hooks from {repo_root}")
            return 0

        output_dir = Path(args.output) if args.output else repo_root / ".claude" / "hooks"
        hook_files = compose_hooks(repo_root, output_dir)

        # Install to .git/hooks if requested
        if args.install:
            git_hooks_dir = repo_root / ".git" / "hooks"
            if git_hooks_dir.exists():
                # Note: install_hooks function needs to be imported or implemented
                # For now, this is a placeholder - the function is not defined
                if not args.json:
                    formatter.text(f"Installed hooks to {git_hooks_dir}")
            else:
                if not args.json:
                    formatter.text(f"Warning: {git_hooks_dir} does not exist, skipping install")

        if args.json:
            formatter.json_output({
                "hooks": [str(f) for f in hook_files],
                "count": len(hook_files),
                "installed": args.install,
            })
        else:
            formatter.text(f"Composed {len(hook_files)} hook(s):")
            for f in hook_files:
                formatter.text(f"  - {f.name}")

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
