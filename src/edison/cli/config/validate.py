"""
Edison config validate command.

SUMMARY: Validate project configuration

Validates the merged configuration against schemas and checks for common issues.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from edison.cli import OutputFormatter, add_repo_root_flag, get_repo_root
from edison.core.config import ConfigManager

SUMMARY = "Validate project configuration"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation (treat warnings as errors)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors, no success messages",
    )
    add_repo_root_flag(parser)


def _check_required_fields(config: dict) -> List[Tuple[str, str]]:
    """Check for required fields and return list of (level, message) tuples."""
    issues: List[Tuple[str, str]] = []
    
    # Check project name
    project = config.get("project", {})
    if not project.get("name"):
        issues.append(("warning", "project.name is not set"))
    
    # Check paths
    paths = config.get("paths", {})
    if not paths.get("project_config_dir"):
        issues.append(("warning", "paths.project_config_dir is not set"))
    
    return issues


def _check_consistency(config: dict) -> List[Tuple[str, str]]:
    """Check for configuration consistency issues."""
    issues: List[Tuple[str, str]] = []
    
    # Check worktrees configuration
    worktrees = config.get("worktrees", {})
    if worktrees.get("enabled"):
        if not worktrees.get("baseDirectory"):
            issues.append(("warning", "worktrees.enabled but baseDirectory not set"))
    
    # Check database configuration  
    database = config.get("database", {})
    if database.get("enabled") and not database.get("url"):
        issues.append(("error", "database.enabled but database.url not set"))
    
    # Check TDD configuration
    tdd = config.get("tdd", {})
    if tdd.get("enforceRedGreenRefactor") and not tdd.get("requireEvidence"):
        issues.append(("warning", "TDD enforcement enabled but evidence not required"))
    
    return issues


def main(args: argparse.Namespace) -> int:
    """Validate configuration."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    
    try:
        repo_root = get_repo_root(args)
        config_manager = ConfigManager(repo_root)
        
        issues: List[Tuple[str, str]] = []
        
        # Try to load and validate config
        try:
            config = config_manager.load_config(validate=True)
            if not args.quiet:
                formatter.text("✅ Configuration loaded and schema validated")
        except Exception as e:
            issues.append(("error", f"Schema validation failed: {e}"))
            # Try to load without validation to continue checks
            try:
                config = config_manager.load_config(validate=False)
            except Exception:
                formatter.text("❌ Configuration could not be loaded")
                return 1
        
        # Run additional checks
        issues.extend(_check_required_fields(config))
        issues.extend(_check_consistency(config))
        
        # Report issues
        errors = [msg for level, msg in issues if level == "error"]
        warnings = [msg for level, msg in issues if level == "warning"]
        
        if warnings:
            formatter.text(f"\n⚠️  Warnings ({len(warnings)}):")
            for msg in warnings:
                formatter.text(f"   - {msg}")
        
        if errors:
            formatter.text(f"\n❌ Errors ({len(errors)}):")
            for msg in errors:
                formatter.text(f"   - {msg}")
        
        # Determine exit code
        if errors:
            formatter.text("\n❌ Configuration validation failed")
            return 1
        
        if warnings and args.strict:
            formatter.text("\n❌ Configuration has warnings (strict mode)")
            return 1
        
        if not args.quiet:
            if warnings:
                formatter.text("\n✅ Configuration valid (with warnings)")
            else:
                formatter.text("\n✅ Configuration valid")
        
        return 0

    except Exception as e:
        formatter.error(e, error_code="validate_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
