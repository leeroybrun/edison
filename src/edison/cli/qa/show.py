"""
Edison QA show command.

SUMMARY: Show raw QA Markdown
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Show raw QA Markdown"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "qa_id",
        help="QA identifier (e.g., 150-wave1-auth-gate-qa)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)

        from edison.core.task import normalize_record_id
        from edison.core.qa.workflow.repository import QARepository

        qa_id = normalize_record_id("qa", str(args.qa_id))
        repo = QARepository(project_root=project_root)
        path = repo.get_path(qa_id)
        content = path.read_text(encoding="utf-8", errors="strict")

        qa = repo.get(qa_id)

        if formatter.json_mode:
            formatter.json_output(
                {
                    "recordType": "qa",
                    "id": qa_id,
                    "task_id": qa.task_id if qa else None,
                    "path": str(path),
                    "qa": qa.to_dict() if qa else None,
                    "content": content,
                }
            )
        else:
            formatter.text(content)
        return 0
    except Exception as e:
        formatter.error(e, error_code="qa_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

