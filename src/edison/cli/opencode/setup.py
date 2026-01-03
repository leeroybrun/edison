"""
Edison OpenCode setup command.

SUMMARY: Generate project-local OpenCode plugin artifacts for Edison
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_dry_run_flag, add_force_flag, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.utils.io import ensure_directory, write_text
from edison.core.utils.text import render_template_text
from edison.data import read_text as data_read_text

SUMMARY = "Generate project-local OpenCode plugin artifacts for Edison"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply changes without interactive confirmation (still requires --force to overwrite modified files)",
    )
    add_force_flag(parser)
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _is_edison_project(repo_root: Path) -> bool:
    # Minimal, deterministic check (no legacy `.edison/core` paths).
    return (repo_root / ".edison" / "config").exists()


def _render_plugin_template(*, repo_root: Path) -> str:
    template = data_read_text("templates", "opencode/plugin/edison.ts.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        if not _is_edison_project(repo_root):
            raise RuntimeError(f"Not an Edison project: missing {repo_root / '.edison' / 'config'}")

        target = repo_root / ".opencode" / "plugin" / "edison.ts"
        desired = _render_plugin_template(repo_root=repo_root)

        exists = target.exists()
        current = target.read_text(encoding="utf-8") if exists else ""
        needs_write = (not exists) or (current != desired)

        change = {
            "path": str(target),
            "action": ("create" if not exists else ("noop" if not needs_write else "update")),
        }

        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "changes": [change]})
            else:
                formatter.text("[dry-run] Would ensure OpenCode plugin exists:")
                formatter.text(f"  - {change['action']}: {target}")
            return 0

        if not needs_write:
            if args.json:
                formatter.json_output({"status": "ok", "changes": [change]})
            else:
                formatter.text(f"OpenCode plugin already up to date: {target}")
            return 0

        if exists and current != desired and not bool(getattr(args, "force", False)):
            if args.json:
                formatter.json_output(
                    {
                        "status": "blocked",
                        "error": "Target file differs; refuse to overwrite without --force",
                        "path": str(target),
                    }
                )
            else:
                formatter.text(f"Refusing to overwrite modified file without --force: {target}")
                formatter.text("Re-run with `--force --yes` to overwrite with the generated plugin.")
            return 1

        if not bool(getattr(args, "yes", False)):
            if args.json:
                formatter.json_output(
                    {
                        "status": "confirm",
                        "changes": [change],
                        "note": "Re-run with --yes to apply",
                    }
                )
            else:
                formatter.text("Planned changes:")
                formatter.text(f"  - {change['action']}: {target}")
                formatter.text("Re-run with `--yes` to apply.")
            return 1

        ensure_directory(target.parent)
        write_text(target, desired)

        if args.json:
            formatter.json_output({"status": "ok", "changes": [change]})
        else:
            formatter.text(f"Wrote OpenCode plugin: {target}")
            formatter.text("OpenCode will auto-discover project-local plugins under `.opencode/plugin/*.{js,ts}`.")

        return 0

    except Exception as e:
        formatter.error(e, error_code="opencode_setup_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

