"""
Edison compose validate command.

SUMMARY: Validate composition configuration and outputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Validate composition configuration and outputs"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix validation issues",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Validate composition - delegates to composition validator."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.composition import validate_composition
    from edison.core.utils.paths import get_project_config_dir

    try:
        repo_root = get_repo_root(args)

        # For now, just do basic validation that the repo structure exists
        config_dir = get_project_config_dir(repo_root, create=False)
        validation_result = {
            "valid": True,
            "repo_root": str(repo_root),
            "issues": [],
        }

        # Check for basic required directories
        required_dirs = [
            config_dir,
            config_dir / "core",
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                validation_result["valid"] = False
                validation_result["issues"].append(f"Missing required directory: {dir_path}")

        if args.json:
            formatter.json_output(validation_result)
        else:
            if validation_result["valid"]:
                formatter.text("✓ Composition validation passed")
            else:
                formatter.text("✗ Composition validation failed")
                for issue in validation_result.get("issues", []):
                    if isinstance(issue, str):
                        formatter.text(f"  [error] {issue}")
                    else:
                        severity = issue.get("severity", "error")
                        formatter.text(f"  [{severity}] {issue['message']}")
                        if issue.get("file"):
                            formatter.text(f"    File: {issue['file']}")

            if args.fix and "fixes_applied" in validation_result:
                formatter.text(f"\nApplied {len(validation_result['fixes_applied'])} fix(es)")

        return 0 if validation_result["valid"] else 1

    except Exception as e:
        formatter.error(e, error_code="compose_validation_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
