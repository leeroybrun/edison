"""
Edison evidence show command.

SUMMARY: Display evidence content for review/debugging
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Display evidence content for review/debugging"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--file", dest="filename", help="Evidence filename within the round directory")
    group.add_argument("--command", dest="command_name", help="CI command name (mapped via validation.evidence.files)")
    parser.add_argument("--raw", action="store_true", help="Print raw file content without parsing")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _list_round_files(round_dir: Path) -> list[str]:
    try:
        return sorted([p.name for p in round_dir.iterdir() if p.is_file()])
    except Exception:
        return []


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        raw_task_id = str(args.task_id)
        task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=raw_task_id)
        filename = getattr(args, "filename", None)
        command_name = getattr(args, "command_name", None)
        raw = bool(getattr(args, "raw", False))

        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence.command_evidence import parse_command_evidence
        from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir

        key = current_snapshot_key(project_root=project_root)
        snap_dir = snapshot_dir(project_root=project_root, key=key)

        if command_name and not filename:
            qa = QAConfig(repo_root=project_root)
            evidence_files = (qa.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
            if not isinstance(evidence_files, dict):
                evidence_files = {}
            filename = str(evidence_files.get(str(command_name)) or f"command-{command_name}.txt").strip()

        if not filename:
            files = _list_round_files(snap_dir) if snap_dir.exists() else []
            if formatter.json_mode:
                formatter.json_output(
                    {"taskId": task_id, "snapshotDir": str(snap_dir.relative_to(project_root)), "files": files}
                )
            else:
                formatter.text(f"Evidence snapshot files for {task_id}:")
                formatter.text(f"- Snapshot: {snap_dir.relative_to(project_root)}")
                for f in files:
                    formatter.text(f"- {f}")
                formatter.text("Pick one: `edison evidence show <task> --file <name>` or `--command <ci-command>`")
            return 1

        evidence_path = snap_dir / str(filename)
        if not evidence_path.exists():
            available = _list_round_files(snap_dir) if snap_dir.exists() else []
            raise RuntimeError(
                f"Evidence file not found in current snapshot: {filename}. "
                + (f"Available: {', '.join(available)}" if available else "")
            )

        text = evidence_path.read_text(encoding="utf-8", errors="replace")
        if raw:
            if formatter.json_mode:
                formatter.json_output(
                    {
                        "taskId": task_id,
                        "snapshotDir": str(snap_dir.relative_to(project_root)),
                        "file": str(filename),
                        "raw": text,
                    }
                )
            else:
                formatter.text(text.rstrip("\n"))
            return 0

        parsed = parse_command_evidence(evidence_path)
        if parsed is None:
            if formatter.json_mode:
                formatter.json_output(
                    {
                        "taskId": task_id,
                        "snapshotDir": str(snap_dir.relative_to(project_root)),
                        "file": str(filename),
                        "raw": text,
                    }
                )
            else:
                formatter.text(text.rstrip("\n"))
            return 0

        if formatter.json_mode:
            formatter.json_output(
                {
                    "taskId": task_id,
                    "snapshotDir": str(snap_dir.relative_to(project_root)),
                    "file": str(filename),
                    **parsed,
                }
            )
            return 0

        formatter.text(f"Evidence (snapshot): {task_id} / {filename}")
        formatter.text(f"- command: {parsed.get('commandName', 'unknown')} (exit {parsed.get('exitCode', 'unknown')})")
        cmd = str(parsed.get("command", "") or "").strip()
        if cmd:
            formatter.text(f"- run: {cmd}")
        formatter.text("---- output ----")
        formatter.text((parsed.get("output") or "").rstrip("\n"))
        return 0

    except Exception as e:
        formatter.error(e, error_code="evidence_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
