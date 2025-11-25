"""
Edison validators run command.

SUMMARY: Run a specific validator
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Run validator - delegates to validation library."""
    from edison.core.qa import validator
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

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

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Validator: {args.validator_id}")
            print(f"  Task: {args.task_id}")
            print(f"  Model: {config.get('model', 'default')}")
            print(f"  Interface: {config.get('interface', 'clink')}")
            print(f"  Blocking: {config.get('blocksOnFail', False)}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
