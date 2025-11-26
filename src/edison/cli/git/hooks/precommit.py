"""
Edison git pre-commit hook.

SUMMARY: Run pre-commit validations
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Run pre-commit validations"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation checks",
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
    """Run pre-commit hook validations."""
    from edison.core.git import status as git_status
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Get staged files
        result = git_status.get_status(repo_root=repo_root)
        staged_files = result.get("staged", [])

        if not staged_files:
            if args.json:
                print(json.dumps({"status": "no_files", "message": "No files staged"}))
            else:
                print("No files staged for commit")
            return 0

        # Basic validations
        issues = []

        # Check for common issues
        for file_path in staged_files:
            # Check for sensitive files
            if any(pattern in file_path.lower() for pattern in [".env", "credentials", "secrets"]):
                issues.append(f"Sensitive file detected: {file_path}")

            # Check for large files (>10MB)
            full_path = repo_root / file_path
            if full_path.exists() and full_path.is_file():
                size_mb = full_path.stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    issues.append(f"Large file detected ({size_mb:.1f}MB): {file_path}")

        if args.skip_validation:
            issues = []

        result_data = {
            "status": "failed" if issues else "passed",
            "staged_count": len(staged_files),
            "issues": issues,
        }

        if args.json:
            print(json.dumps(result_data, indent=2))
        else:
            if issues:
                print("Pre-commit validation failed:")
                for issue in issues:
                    print(f"  ✗ {issue}")
                print("\nUse --skip-validation to bypass these checks")
            else:
                print(f"Pre-commit validation passed ({len(staged_files)} files)")

        return 1 if issues else 0

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
