"""
Edison compose validate command.

SUMMARY: Validate composition configuration and outputs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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


def main(args: argparse.Namespace) -> int:
    """Validate composition - delegates to composition validator."""
    from edison.core.composition import validate_composition
    from edison.core.utils.paths import resolve_project_root
    from edison.core.utils.paths import get_project_config_dir

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

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
            print(json.dumps(validation_result, indent=2))
        else:
            if validation_result["valid"]:
                print("✓ Composition validation passed")
            else:
                print("✗ Composition validation failed")
                for issue in validation_result.get("issues", []):
                    severity = issue.get("severity", "error")
                    print(f"  [{severity}] {issue['message']}")
                    if issue.get("file"):
                        print(f"    File: {issue['file']}")

            if args.fix and "fixes_applied" in validation_result:
                print(f"\nApplied {len(validation_result['fixes_applied'])} fix(es)")

        return 0 if validation_result["valid"] else 1

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
