"""
Edison compose hooks command.

SUMMARY: Compose git hooks from configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    """Compose git hooks - delegates to composition engine."""
    from edison.core.ide.hooks import compose_hooks
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        if args.dry_run:
            if args.json:
                print(json.dumps({"status": "dry-run", "repo_root": str(repo_root)}))
            else:
                print(f"[dry-run] Would compose hooks from {repo_root}")
            return 0

        output_dir = Path(args.output) if args.output else repo_root / ".claude" / "hooks"
        hook_files = compose_hooks(repo_root, output_dir)

        # Install to .git/hooks if requested
        if args.install:
            git_hooks_dir = repo_root / ".git" / "hooks"
            if git_hooks_dir.exists():
                install_hooks(output_dir, git_hooks_dir)
                if not args.json:
                    print(f"Installed hooks to {git_hooks_dir}")
            else:
                if not args.json:
                    print(f"Warning: {git_hooks_dir} does not exist, skipping install")

        if args.json:
            print(json.dumps({
                "hooks": [str(f) for f in hook_files],
                "count": len(hook_files),
                "installed": args.install,
            }, indent=2))
        else:
            print(f"Composed {len(hook_files)} hook(s):")
            for f in hook_files:
                print(f"  - {f.name}")

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
