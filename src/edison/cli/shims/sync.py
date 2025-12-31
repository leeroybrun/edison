"""
Edison shims sync command.

SUMMARY: Generate repo-local shell shims into .edison/_generated/shims
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.shims import ShimService

SUMMARY = "Generate repo-local shell shims"


def register_args(parser: argparse.ArgumentParser) -> None:
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    repo_root = get_repo_root(args)

    svc = ShimService(project_root=repo_root)
    written = svc.sync()

    if formatter.json_mode:
        formatter.json_output(
            {
                "enabled": svc.enabled(),
                "outputDir": str(svc.output_dir()),
                "written": [str(p) for p in written],
            }
        )
        return 0

    formatter.text("✓ Shims synced")
    formatter.text(f"  Dir: {svc.output_dir()}")
    if written:
        formatter.text("  Installed:")
        for p in sorted(written):
            formatter.text(f"    - {p.name}")
    else:
        formatter.text("  (No shims enabled)")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

