"""
Edison qa run command.

SUMMARY: Run a specific validator
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa.engines import EngineRegistry
from edison.core.qa.evidence import EvidenceService

SUMMARY = "Run a specific validator"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "validator_id",
        help="Validator identifier to run (e.g., global-codex, security)",
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
        "--worktree",
        type=str,
        help="Path to git worktree (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be run without executing",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Run validator - delegates to validation library."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        # Create engine registry
        registry = EngineRegistry(project_root=repo_root)

        # Get validator configuration
        config = registry.get_validator(args.validator_id)

        if not config:
            raise ValueError(f"Unknown validator: {args.validator_id}")

        # Determine worktree path
        worktree_path = Path(args.worktree) if args.worktree else repo_root

        if args.dry_run:
            # Dry run - just show configuration
            result = {
                "validator_id": args.validator_id,
                "task_id": args.task_id,
                "session_id": args.session,
                "round": args.round,
                "worktree": str(worktree_path),
                "config": {
                    "name": config.name,
                    "engine": config.engine,
                    "fallback_engine": config.fallback_engine,
                    "wave": config.wave,
                    "blocking": config.blocking,
                    "always_run": config.always_run,
                    "timeout": config.timeout,
                    "prompt": config.prompt,
                    "zen_role": config.zen_role,
                },
                "status": "dry_run",
                "message": f"Validator {args.validator_id} would run with engine {config.engine}",
            }
        else:
            # Create evidence service if session provided
            evidence_service = None
            if args.session:
                evidence_service = EvidenceService(args.task_id, repo_root)

            # Run the validator
            validation_result = registry.run_validator(
                validator_id=args.validator_id,
                task_id=args.task_id,
                session_id=args.session or "cli",
                worktree_path=worktree_path,
                round_num=args.round,
                evidence_service=evidence_service,
            )

            result = {
                "validator_id": args.validator_id,
                "task_id": args.task_id,
                "session_id": args.session,
                "round": args.round,
                "verdict": validation_result.verdict,
                "summary": validation_result.summary,
                "duration": validation_result.duration,
                "exit_code": validation_result.exit_code,
                "error": validation_result.error,
                "status": "completed",
            }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"Validator: {args.validator_id}")
            formatter.text(f"  Task: {args.task_id}")
            formatter.text(f"  Engine: {config.engine}")
            if config.fallback_engine:
                formatter.text(f"  Fallback: {config.fallback_engine}")
            formatter.text(f"  Wave: {config.wave}")
            formatter.text(f"  Blocking: {config.blocking}")

            if not args.dry_run:
                formatter.text(f"  Verdict: {result.get('verdict', 'N/A')}")
                formatter.text(f"  Duration: {result.get('duration', 0):.2f}s")
                if result.get('error'):
                    formatter.text(f"  Error: {result['error']}")

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
