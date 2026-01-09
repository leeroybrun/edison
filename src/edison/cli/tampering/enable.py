"""
Edison tampering enable command.

SUMMARY: Enable tampering protection

Enables tampering protection for the Edison project by updating the
tampering configuration file and triggering settings re-composition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.config.domains import TamperingConfig

SUMMARY = "Enable tampering protection"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    add_json_flag(parser)
    add_repo_root_flag(parser)
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not sync platform settings after enabling",
    )


def _sync_platform_settings(repo_root: Path) -> Optional[Path]:
    """Sync platform settings to include tampering deny rules.

    Args:
        repo_root: Project root directory.

    Returns:
        Path to the written settings file, or None if failed.
    """
    try:
        from edison.cli.compose._context import build_compose_context
        from edison.core.adapters.components.settings import SettingsComposer

        context = build_compose_context(repo_root=repo_root)
        composer = SettingsComposer(context)
        return composer.write_settings_file()
    except Exception:
        # Non-fatal: tampering is enabled even if settings sync fails
        return None


def main(args: argparse.Namespace) -> int:
    """Execute the tampering enable command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        tampering_config = TamperingConfig(repo_root=repo_root)

        # Enable tampering protection
        tampering_config.set_enabled(True)

        # Get the config file path for output
        config_path = tampering_config._get_config_file_path()

        # Sync platform settings to include deny rules
        settings_path: Optional[Path] = None
        if not getattr(args, "no_sync", False):
            settings_path = _sync_platform_settings(repo_root)

        if formatter.json_mode:
            output = {
                "enabled": True,
                "configPath": str(config_path),
                "mode": tampering_config.mode,
                "protectedDir": str(tampering_config.protected_dir),
            }
            if settings_path:
                output["settingsPath"] = str(settings_path)
            formatter.json_output(output)
        else:
            formatter.text("Tampering protection enabled.")
            formatter.text(f"  Config: {config_path}")
            formatter.text(f"  Mode: {tampering_config.mode}")
            formatter.text(f"  Protected dir: {tampering_config.protected_dir}")
            if settings_path:
                formatter.text(f"  Settings: {settings_path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="tampering_enable_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
