"""
Edison orchestrator profiles command.

SUMMARY: List available orchestrator profiles
"""

from __future__ import annotations

import argparse
import sys

from edison.core.config.domains import OrchestratorConfig
from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
)

SUMMARY = "List available orchestrator profiles"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List available orchestrator profiles."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:

        repo_root = get_repo_root(args)
        config = OrchestratorConfig(repo_root)

        profiles = config.list_profiles()
        default_profile = config.get_default_profile_name()

        if formatter.json_mode:
            formatter.json_output({
                "default": default_profile,
                "profiles": profiles,
            })
        else:
            formatter.text("Available orchestrator profiles:")
            for profile in profiles:
                marker = " (default)" if profile == default_profile else ""
                formatter.text(f"  - {profile}{marker}")

        return 0

    except ValueError as e:
        # No orchestrator config found
        if formatter.json_mode:
            formatter.json_output({"default": None, "profiles": [], "error": str(e)})
        else:
            formatter.text("No orchestrator configuration found.")
            formatter.text("Run 'edison init' to set up orchestrator profiles.")
        return 0

    except Exception as e:
        formatter.error(e, error_code="config_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
