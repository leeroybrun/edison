"""
Edison qa run command.

SUMMARY: Run a specific validator
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa import validator

SUMMARY = "Run a specific validator"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "validator_id",
        help="Validator identifier to run (e.g., codex-global, security)",
    )
    parser.add_argument(
        "task_id",
        help="Task identifier to validate",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID context",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Override the validator model (codex, claude, gemini)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Run validator - delegates to validation library."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        # Get validator configuration
        config = validator.get_validator_config(args.validator_id, repo_root=repo_root)

        if not config:
            raise ValueError(f"Unknown validator: {args.validator_id}")

        result = {
            "validator_id": args.validator_id,
            "task_id": args.task_id,
            "session_id": args.session,
            "round": args.round,
            "config": config,
            "status": "ready",
            "message": f"Validator {args.validator_id} is configured and ready to run",
        }

        if args.model:
            result["model_override"] = args.model

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"Validator: {args.validator_id}")
            formatter.text(f"  Task: {args.task_id}")
            formatter.text(f"  Model: {config.get('model', 'default')}")
            formatter.text(f"  Interface: {config.get('interface', 'clink')}")
            formatter.text(f"  Blocking: {config.get('blocksOnFail', False)}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="run_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
