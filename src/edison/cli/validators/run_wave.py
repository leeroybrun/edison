"""
Edison validators run-wave command.

SUMMARY: Run validator wave (multiple validators in sequence)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SUMMARY = "Run validator wave (multiple validators in sequence)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier to validate",
    )
    parser.add_argument(
        "--wave",
        type=str,
        help="Wave configuration (validator IDs comma-separated or wave name)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run validators in parallel (default: sequential)",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID context (optional)",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: create new round)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def _parse_wave_config(wave_str: str) -> List[str]:
    """Parse wave configuration string into list of validator IDs."""
    if not wave_str:
        return []

    # Simple comma-separated list
    if "," in wave_str:
        return [v.strip() for v in wave_str.split(",") if v.strip()]

    # Predefined wave names could be added here
    # For now, treat as single validator ID
    return [wave_str.strip()]


def main(args: argparse.Namespace) -> int:
    """Run validator wave - orchestrates multiple validators."""
    from edison.core.qa import validator, rounds
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Determine round number
        round_num = args.round if args.round else rounds.next_round(args.task_id)

        # Build validator roster
        roster = validator.build_validator_roster(
            args.task_id,
            session_id=args.session,
        )

        if "error" in roster:
            raise RuntimeError(roster["error"])

        # Parse wave configuration
        wave_validators = _parse_wave_config(args.wave) if args.wave else []

        # If wave specified, filter roster to those validators
        if wave_validators:
            roster = {
                "alwaysRequired": [
                    v for v in roster.get("alwaysRequired", [])
                    if v["id"] in wave_validators
                ],
                "triggeredBlocking": [
                    v for v in roster.get("triggeredBlocking", [])
                    if v["id"] in wave_validators
                ],
                "triggeredOptional": [
                    v for v in roster.get("triggeredOptional", [])
                    if v["id"] in wave_validators
                ],
            }

        # Flatten validator list for wave execution
        all_validators = (
            roster.get("alwaysRequired", []) +
            roster.get("triggeredBlocking", []) +
            roster.get("triggeredOptional", [])
        )

        # Build waves array for output (single wave for now, but structure supports multiple)
        waves = [{
            "wave": wave_validators if wave_validators else "all",
            "validators": all_validators,
            "mode": "parallel" if args.parallel else "sequential",
        }] if all_validators else []

        result = {
            "task_id": args.task_id,
            "session_id": args.session,
            "round": round_num,
            "waves": waves,
            "total_validators": len(all_validators),
            "status": "ready",
            "message": f"Ready to run wave of {len(all_validators)} validators",
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Validator wave for {args.task_id} (round {round_num}):")
            for wave in waves:
                print(f"  Mode: {wave['mode']}")
                print(f"  Validators: {len(wave['validators'])}")
                for v in wave['validators']:
                    print(f"    - {v['id']} ({v.get('model', 'unknown')})")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
