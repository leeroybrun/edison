"""
Project initialization command.

SUMMARY: Initialize an Edison project and wire up MCP integration.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from edison.core.paths.project import get_project_config_dir
from edison.data import get_data_path
from edison.core.templates.mcp_config import configure_mcp_json

SUMMARY = "Initialize an Edison project (creates config + MCP setup)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register CLI arguments for ``edison init``."""

    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Project directory to initialize (defaults to current directory)",
    )
    parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip MCP configuration",
    )
    parser.add_argument(
        "--mcp-script",
        action="store_true",
        help="Use script-based command variant when available",
    )


def _ensure_structure(project_root: Path) -> Path:
    """Create base .edison structure and return config root."""

    config_root = get_project_config_dir(project_root)

    for rel in ["config", "guidelines", "_generated", "constitutions", "scripts/zen"]:
        (config_root / rel).mkdir(parents=True, exist_ok=True)

    gitignore = config_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# Edison generated content\n_generated/\n.cache/\n__pycache__/\n*.pyc\n", encoding="utf-8")

    return config_root


def _seed_config_files(config_root: Path) -> None:
    """Copy packaged config templates into the project (idempotent)."""

    config_dir = config_root / "config"
    data_config_dir = get_data_path("config")

    yaml_files = list(data_config_dir.glob("*.yaml")) + list(data_config_dir.glob("*.yml"))
    for yaml_path in yaml_files:
        target = config_dir / (yaml_path.stem + ".yml")
        if target.exists():
            continue
        target.write_text(yaml_path.read_text(encoding="utf-8"), encoding="utf-8")


def _copy_mcp_scripts(config_root: Path) -> None:
    """Place bundled MCP helper scripts under .edison/scripts/zen for shell mode."""

    dest_dir = config_root / "scripts" / "zen"
    src_dir_candidates = [
        Path(__file__).resolve().parents[4] / "scripts" / "zen",
    ]

    for src_dir in src_dir_candidates:
        if not src_dir.exists():
            continue
        for script in src_dir.glob("*.sh"):
            dest = dest_dir / script.name
            if dest.exists():
                continue
            shutil.copy2(script, dest)


def _configure_mcp(project_root: Path, *, use_script: bool) -> tuple[bool, str | None]:
    """Configure MCP entries; returns (success, warning_message)."""

    warning: str | None = None

    try:
        result = configure_mcp_json(
            project_root=project_root,
            prefer_scripts=use_script,
            dry_run=False,
        )
        added = result.get("_meta", {}).get("added")
        if added:
            print("✅ Configured .mcp.json with managed servers")
        else:
            print("ℹ️  MCP servers already configured in .mcp.json")
        return True, warning
    except Exception as exc:
        warning = f"⚠️  Warning: Could not configure .mcp.json: {exc}"
        print(warning)
        print("   Run 'edison mcp configure' manually.")
        return False, warning


def _run_initial_composition(project_root: Path) -> None:
    """Invoke compose all to generate starter artifacts."""

    from argparse import Namespace
    from edison.cli.compose import all as compose_all

    args = Namespace(
        agents=False,
        validators=False,
        orchestrator=False,
        constitutions=False,
        guidelines=False,
        platforms=None,
        claude=False,
        cursor=False,
        zen=False,
        dry_run=False,
        json=False,
        repo_root=str(project_root),
    )

    compose_all.main(args)


def main(args: argparse.Namespace) -> int:
    """Initialize Edison in the given project directory."""

    project_root = Path(args.project_path).expanduser().resolve()

    try:
        config_root = _ensure_structure(project_root)
        _seed_config_files(config_root)
        _copy_mcp_scripts(config_root)
        print(f"✅ Created {config_root} structure")

        if not args.skip_mcp:
            success, warning = _configure_mcp(project_root, use_script=args.mcp_script)
        else:
            print("ℹ️  Skipped MCP setup (--skip-mcp)")

        print("\nRunning initial composition...")
        _run_initial_composition(project_root)

        print("\n✅ Edison initialized successfully!")
        print("\nNext steps:")
        print("  1. Review .edison/config/*.yml")
        print("  2. Run 'edison compose all' after adjusting configuration")
        print("  3. Start a session: edison session create <session-id>")
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
