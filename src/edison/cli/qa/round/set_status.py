"""Append a round record to a QA brief (status/notes only).

This records QA history (approve/reject/blocked/pending) without creating or
modifying evidence directories.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._worktree_enforcement import maybe_enforce_session_worktree
from edison.core.qa.workflow.repository import QARepository

SUMMARY = "Append a round record to the QA brief (status/notes only)"


def _allowed_round_statuses(*, repo_root: Path) -> set[str]:
    from edison.core.schemas.validation import load_schema

    schema = load_schema("reports/validator-report.schema.yaml", repo_root=repo_root)
    verdict = (schema.get("properties") or {}).get("verdict") or {}
    values = verdict.get("enum") or []
    return {str(v) for v in values}


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument(
        "--status",
        type=str,
        required=True,
        help="Round status (one of: approve, reject, blocked, pending)",
    )
    parser.add_argument("--note", type=str, help="Notes for the round (e.g., validator names)")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        blocked = maybe_enforce_session_worktree(
            project_root=repo_root,
            command_name="qa round set-status",
            args=args,
            json_mode=bool(formatter.json_mode),
        )
        if blocked is not None:
            return int(blocked)

        allowed = _allowed_round_statuses(repo_root=repo_root)
        status = str(args.status or "").strip()
        if status not in allowed:
            raise ValueError(f"Invalid round status: {status}. Valid values: {', '.join(sorted(allowed))}")

        qa_repo = QARepository(project_root=repo_root)
        qa_id = f"{args.task_id}-qa"
        updated = qa_repo.append_round(
            qa_id,
            status=status,
            notes=getattr(args, "note", None),
            create_evidence_dir=False,
        )

        payload = {"taskId": args.task_id, "round": updated.round, "status": status}
        formatter.json_output(payload) if formatter.json_mode else formatter.text(
            f"Appended round {updated.round} for {args.task_id} ({status})"
        )
        return 0
    except Exception as e:
        formatter.error(e, error_code="round_set_status_error")
        return 1

