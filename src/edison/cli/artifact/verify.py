"""
Edison artifact verify command.

SUMMARY: Verify REQUIRED FILL sections are complete
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.artifacts import find_missing_required_sections

SUMMARY = "Verify REQUIRED FILL sections are complete"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "path",
        help="Artifact file path (absolute or repo-relative)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        raw_path = Path(str(args.path)).expanduser()
        path = raw_path if raw_path.is_absolute() else (repo_root / raw_path)
        content = path.read_text(encoding="utf-8", errors="strict")

        missing = find_missing_required_sections(content)
        payload = {
            "path": str(path),
            "missingRequiredSections": missing,
            "ok": not missing,
        }

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            if missing:
                formatter.text(f"Missing required sections: {', '.join(missing)}")
            else:
                formatter.text("OK")

        return 0 if not missing else 1
    except Exception as e:
        formatter.error(e, error_code="artifact_verify_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

