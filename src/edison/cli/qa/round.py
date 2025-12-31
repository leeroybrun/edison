"""
Edison qa round command.

SUMMARY: Manage QA rounds

NOTE: This CLI delegates to QARepository for round record management
and EvidenceService for evidence directory management.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa.evidence import EvidenceService
from edison.core.qa.workflow.repository import QARepository

SUMMARY = "Manage QA rounds"

def _allowed_round_statuses(*, repo_root: Path) -> set[str]:
    """Return the canonical round status vocabulary.

    We align the QA round status with the validator report verdict enum to avoid
    duplicated vocabularies.
    """
    from edison.core.schemas.validation import load_schema

    schema = load_schema("reports/validator-report.schema.yaml", repo_root=repo_root)
    verdict = (schema.get("properties") or {}).get("verdict") or {}
    values = verdict.get("enum") or []
    return {str(v) for v in values}


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Round status (one of: approve, reject, blocked, pending)",
    )
    parser.add_argument(
        "--note",
        type=str,
        help="Notes for the round (e.g., validator names)",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Create new evidence round directory",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all rounds",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Show current round number",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Manage QA rounds - uses EvidenceService for evidence and QARepository for records."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        qa_repo = QARepository(project_root=repo_root)
        ev_svc = EvidenceService(args.task_id, project_root=repo_root)

        # Construct QA ID from task ID (convention: task_id + "-qa")
        qa_id = f"{args.task_id}-qa"

        # Default behavior: append a new round with given status
        if not args.new and not args.list and not args.current:
            status = args.status or "pending"
            allowed = _allowed_round_statuses(repo_root=repo_root)
            if status not in allowed:
                raise ValueError(f"Invalid round status: {status}. Valid values: {', '.join(sorted(allowed))}")

            # Use QARepository to append round (no direct file manipulation)
            updated_qa = qa_repo.append_round(
                qa_id,
                status=status,
                notes=args.note,
                create_evidence_dir=False,
            )

            result = {
                "taskId": args.task_id,
                "round": updated_qa.round,
                "status": status,
            }
            formatter.json_output(result) if formatter.json_mode else formatter.text(
                "\n".join(
                    [
                        f"Appended round {updated_qa.round} for {args.task_id}",
                        "  Note: no evidence directory was created (use `edison qa round --new` to create round-N/)",
                    ]
                )
            )

        elif args.new:
            status = args.status or "pending"
            allowed = _allowed_round_statuses(repo_root=repo_root)
            if status not in allowed:
                raise ValueError(f"Invalid round status: {status}. Valid values: {', '.join(sorted(allowed))}")

            # Canonical behavior: create a new round in the QA record AND ensure the
            # corresponding evidence directory exists.
            updated_qa = qa_repo.append_round(
                qa_id,
                status=status,
                notes=args.note,
                create_evidence_dir=True,
            )
            round_num = updated_qa.round
            round_path = ev_svc.ensure_round(round_num)

            # Update metadata using EvidenceService method (best-effort)
            ev_svc.update_metadata(round_num)

            result = {
                "created": str(round_path),
                "round": round_num,
            }
            formatter.json_output(result) if formatter.json_mode else formatter.text(
                f"Created round {round_num} for {args.task_id}\n  Path: {round_path}"
            )

        elif args.list:
            # Merge rounds from QA record history with evidence directories on disk.
            history = qa_repo.list_rounds(qa_id)
            by_round: dict[int, dict] = {}
            for r in history:
                try:
                    n = int(r.get("round") or 0)
                except Exception:
                    continue
                if n:
                    by_round[n] = dict(r)

            evidence_nums: list[int] = []
            for p in ev_svc.list_rounds():
                try:
                    evidence_nums.append(int(str(p.name).replace("round-", "")))
                except Exception:
                    continue

            combined_nums = sorted(set(evidence_nums) | set(by_round.keys()))
            combined: list[dict] = []
            for n in combined_nums:
                row = dict(by_round.get(n) or {"round": n, "status": "unknown"})
                row["round"] = n
                combined.append(row)

            if formatter.json_mode:
                formatter.json_output({"rounds": combined})
            else:
                if combined:
                    formatter.text(f"Rounds for {args.task_id}:")
                    for r in combined:
                        status = r.get("status", "unknown")
                        date = r.get("date", "")
                        notes = r.get("notes", "")
                        suffix = f" ({date})" if date else ""
                        formatter.text(f"  - Round {r.get('round')}: {status}{suffix}")
                        if notes:
                            formatter.text(f"      Notes: {notes}")
                else:
                    formatter.text(f"No rounds found for {args.task_id}")

        else:
            # Default: show current round from QA record
            current = qa_repo.get_current_round(qa_id)
            if formatter.json_mode:
                formatter.json_output({
                    "task_id": args.task_id,
                    "current_round": current,
                })
            else:
                formatter.text(f"Current round for {args.task_id}: {current}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="round_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
