"""
Edison git pre-commit hook.

SUMMARY: Run pre-commit validations
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Run pre-commit validations"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation checks",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Run pre-commit hook validations."""
    from edison.core.git import status as git_status

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    repo_root = get_repo_root(args)

    try:
        # Get staged files
        result = git_status.get_status(repo_root=repo_root)
        staged_files = result.get("staged", [])

        if not staged_files:
            formatter.json_output({"status": "no_files", "message": "No files staged"}) if formatter.json_mode else formatter.text("No files staged for commit")
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

        if formatter.json_mode:
            formatter.json_output(result_data)
        else:
            if issues:
                formatter.text("Pre-commit validation failed:")
                for issue in issues:
                    formatter.text(f"  - {issue}")
                formatter.text("\nUse --skip-validation to bypass these checks")
            else:
                formatter.text(f"Pre-commit validation passed ({len(staged_files)} files)")

        return 1 if issues else 0

    except Exception as e:
        formatter.error(e, error_code="precommit_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
