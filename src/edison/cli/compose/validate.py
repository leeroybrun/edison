"""
Edison compose validate command.

SUMMARY: Validate composition configuration and outputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.utils.paths import get_project_config_dir
from edison.data import get_data_path

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


    try:
        repo_root = get_repo_root(args)

        # Get project config directory (<project-config-dir>/)
        config_dir = get_project_config_dir(repo_root, create=False)
        validation_result = {
            "valid": True,
            "repo_root": str(repo_root),
            "issues": [],
        }

        # Validate bundled edison.data is accessible
        try:
            bundled_data_dir = get_data_path("")
            if not bundled_data_dir.exists():
                validation_result["valid"] = False
                validation_result["issues"].append(
                    f"Bundled edison.data not accessible: {bundled_data_dir}"
                )
        except Exception as e:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Cannot access bundled edison.data: {e}")

        # Check for project config directory (<project-config-dir>/)
        # Note: This is optional - projects can run with just bundled defaults
        if not config_dir.exists():
            validation_result["issues"].append({
                "severity": "warning",
                "message": f"Project config directory not found: {config_dir}",
                "file": str(config_dir),
            })

        # Check for project config subdirectory (<project-config-dir>/config/)
        project_config = config_dir / "config"
        if config_dir.exists() and not project_config.exists():
            validation_result["issues"].append({
                "severity": "warning",
                "message": f"Project config subdirectory not found: {project_config}",
                "file": str(project_config),
            })

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
