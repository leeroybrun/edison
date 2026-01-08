"""
Edison evidence status command.

SUMMARY: Check evidence completeness and command success
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Check evidence completeness and command success"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument(
        "--preset",
        help="Explicit validation preset name to use for required-evidence resolution (default: inferred for the task).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        raw_task_id = str(args.task_id)
        task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=raw_task_id)

        from edison.core.qa.evidence.command_status import get_command_evidence_status

        preset_name = getattr(args, "preset", None)
        payload = get_command_evidence_status(
            project_root=project_root,
            task_id=task_id,
            preset_name=str(preset_name).strip() if preset_name else None,
        )
        success = bool(payload.get("success"))

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(f"Evidence status for {task_id} (preset={payload.get('preset')}):")
            formatter.text(f"- Snapshot: {payload.get('snapshotDir')}")
            required = payload.get("requiredCommandEvidence") or []
            if required:
                formatter.text(f"- Required: {', '.join(str(x) for x in required)}")
            missing = payload.get("missing") or []
            invalid = payload.get("invalid") or []
            failed = payload.get("failed") or []
            any_stale = bool(payload.get("anyStale"))
            stale = payload.get("staleEvidence") or []
            if missing:
                formatter.text(f"- Missing: {', '.join(missing)}")
                missing_cmds = payload.get("missingCommands") or []
                if missing_cmds:
                    formatter.text(f"- Missing commands: {', '.join(str(x) for x in missing_cmds)}")
            if invalid:
                formatter.text(f"- Invalid: {', '.join(i['file'] for i in invalid if isinstance(i, dict) and i.get('file'))}")
            if failed:
                formatter.text("- Failed:")
                for f in failed:
                    formatter.text(f"  - {f['file']}: {f['commandName']} (exit {f['exitCode']})")
            if any_stale:
                formatter.text("- Stale (warn-only):")
                for s in stale:
                    if s.get("stale"):
                        formatter.text(f"  - {s.get('file')}: {s.get('reason')}")
            if success:
                formatter.text("All required evidence present and passed.")
            else:
                formatter.text("Fix by running: `edison evidence capture <task>` and reviewing output.")
                formatter.text("For targeted reruns: `edison evidence capture <task> --only <command>`")

        return 0 if success else 1

    except Exception as e:
        formatter.error(e, error_code="evidence_status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
