"""
Edison evidence show command.

SUMMARY: Display evidence content for review/debugging
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Display evidence content for review/debugging"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument("--round", type=int, dest="round_num", help="Explicit round number (default: latest)")
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
        task_id = str(args.task_id)
        round_num = getattr(args, "round_num", None)
        filename = getattr(args, "filename", None)
        command_name = getattr(args, "command_name", None)
        raw = bool(getattr(args, "raw", False))

        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence import EvidenceService, rounds
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

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

        if command_name and not filename:
            qa = QAConfig(repo_root=project_root)
            evidence_files = (qa.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
            if not isinstance(evidence_files, dict):
                evidence_files = {}
            filename = str(evidence_files.get(str(command_name)) or f"command-{command_name}.txt").strip()

        if not filename:
            files = _list_round_files(round_dir)
            if formatter.json_mode:
                formatter.json_output({"taskId": task_id, "round": int(round_num or 1), "files": files})
            else:
                formatter.text(f"Evidence files for {task_id} (round-{round_num}):")
                for f in files:
                    formatter.text(f"- {f}")
                formatter.text("Pick one: `edison evidence show <task> --file <name>` or `--command <ci-command>`")
            return 1

        evidence_path = round_dir / str(filename)
        if not evidence_path.exists():
            available = _list_round_files(round_dir)
            raise RuntimeError(
                f"Evidence file not found: {filename} (round-{round_num}). "
                + (f"Available: {', '.join(available)}" if available else "")
            )

        text = evidence_path.read_text(encoding="utf-8", errors="replace")
        if raw:
            if formatter.json_mode:
                formatter.json_output({"taskId": task_id, "round": int(round_num or 1), "file": str(filename), "raw": text})
            else:
                formatter.text(text.rstrip("\n"))
            return 0

        parsed = parse_command_evidence(evidence_path)
        if parsed is None:
            if formatter.json_mode:
                formatter.json_output({"taskId": task_id, "round": int(round_num or 1), "file": str(filename), "raw": text})
            else:
                formatter.text(text.rstrip("\n"))
            return 0

        if formatter.json_mode:
            formatter.json_output({"taskId": task_id, "round": int(round_num or 1), "file": str(filename), **parsed})
            return 0

        formatter.text(f"Evidence: {task_id} (round-{round_num}) / {filename}")
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

