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

SUMMARY = "Check evidence completeness and command success"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument("--round", type=int, dest="round_num", help="Explicit round number (default: latest)")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        task_id = str(args.task_id)
        round_num = getattr(args, "round_num", None)

        from edison.core.qa.evidence import EvidenceService, rounds
        from edison.core.qa.evidence.command_evidence import parse_command_evidence
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        ev = EvidenceService(task_id=task_id, project_root=project_root)
        round_dir: Path
        if round_num is not None:
            round_dir = ev.get_round_dir(int(round_num))
            if not round_dir.exists():
                raise RuntimeError(f"Round {round_num} does not exist")
        else:
            rd = ev.get_current_round_dir()
            if rd is None:
                raise RuntimeError(f"No evidence round exists. Run `edison evidence init {task_id}` first.")
            round_dir = rd
            round_num = rounds.get_round_number(round_dir)

        # Preset-aware required evidence (single source via policy resolver)
        resolver = ValidationPolicyResolver(project_root=project_root)
        policy = resolver.resolve_for_task(task_id)
        required_files = list(policy.required_evidence or [])

        present: list[str] = []
        missing: list[str] = []
        failed: list[dict[str, Any]] = []
        invalid: list[dict[str, Any]] = []

        for filename in required_files:
            file_path = round_dir / str(filename)
            if not file_path.exists():
                missing.append(str(filename))
                continue

            present.append(str(filename))
            parsed = parse_command_evidence(file_path)
            if parsed is None:
                invalid.append({"file": str(filename), "reason": "unparseable"})
                continue
            exit_code = parsed.get("exitCode")
            if exit_code is not None and int(exit_code) != 0:
                failed.append(
                    {
                        "file": str(filename),
                        "commandName": parsed.get("commandName", "unknown"),
                        "exitCode": int(exit_code),
                    }
                )

        all_present = len(missing) == 0
        all_passed = len(failed) == 0
        all_valid = len(invalid) == 0
        success = all_present and all_passed and all_valid

        payload = {
            "taskId": task_id,
            "round": int(round_num or 1),
            "preset": policy.preset.name,
            "present": present,
            "missing": missing,
            "invalid": invalid,
            "failed": failed,
            "complete": all_present,
            "passed": all_passed,
        }

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(f"Evidence status for {task_id} (round-{round_num}, preset={policy.preset.name}):")
            if missing:
                formatter.text(f"- Missing: {', '.join(missing)}")
            if invalid:
                formatter.text(f"- Invalid: {', '.join(i['file'] for i in invalid)}")
            if failed:
                formatter.text("- Failed:")
                for f in failed:
                    formatter.text(f"  - {f['file']}: {f['commandName']} (exit {f['exitCode']})")
            if success:
                formatter.text("All required evidence present and passed.")
            else:
                formatter.text("Fix by running: `edison evidence capture <task>` and reviewing output (`edison evidence show <task> --command <name>`).")
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
