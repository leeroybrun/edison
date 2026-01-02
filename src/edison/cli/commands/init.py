"""
Project initialization command.

SUMMARY: Initialize an Edison project with interactive setup wizard.

This command runs the setup questionnaire by default (interactive mode).
Use --non-interactive to skip the questionnaire and use bundled defaults.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

from edison.cli import OutputFormatter
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.io import ensure_directory
from edison.data import get_data_path

SUMMARY = "Initialize an Edison project (interactive setup wizard)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register CLI arguments for ``edison init``."""

    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Project directory to initialize (defaults to current directory)",
    )
    
    # Interactive mode control
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip prompting; write recommended defaults and detected values (no interactive questions)",
    )
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Include advanced configuration questions",
    )
    
    # File handling
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config files without prompting",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing config files instead of skipping",
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Re-run questionnaire on an existing project",
    )
    
    # MCP options
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
    
    # Skip composition
    parser.add_argument(
        "--skip-compose",
        action="store_true",
        help="Skip running initial composition",
    )

    # Worktree bootstrap
    parser.add_argument(
        "--enable-worktrees",
        action="store_true",
        help="Enable worktrees in generated config (useful with --non-interactive)",
    )
    parser.add_argument(
        "--disable-worktrees",
        action="store_true",
        help="Disable worktrees in generated config (useful with --non-interactive)",
    )
    parser.add_argument(
        "--skip-worktree-meta-init",
        action="store_true",
        help="Do not run `edison git worktree-meta-init` even if worktrees are enabled",
    )


def _ensure_structure(project_root: Path) -> Path:
    """Create base `<project-config-dir>/` structure and return config root."""
    config_root = get_project_config_dir(project_root)

    for rel in ["config", "guidelines", "_generated", "constitutions", "scripts/pal"]:
        (config_root / rel).mkdir(parents=True, exist_ok=True)

    gitignore = config_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# Edison generated content\n_generated/\n.cache/\n__pycache__/\n*.pyc\n",
            encoding="utf-8"
        )

    return config_root


def _copy_mcp_scripts(config_root: Path) -> None:
    """Place bundled MCP helper scripts under `<project-config-dir>/scripts/pal` for shell mode."""
    dest_dir = config_root / "scripts" / "pal"
    src_dir_candidates = [
        Path(__file__).resolve().parents[4] / "scripts" / "pal",
    ]

    for src_dir in src_dir_candidates:
        if not src_dir.exists():
            continue
        for script in src_dir.glob("*.sh"):
            dest = dest_dir / script.name
            if dest.exists():
                continue
            shutil.copy2(script, dest)


def _configure_mcp(
    project_root: Path, 
    *, 
    use_script: bool, 
    formatter: OutputFormatter
) -> tuple[bool, Optional[str]]:
    """Configure MCP entries; returns (success, warning_message)."""
    from edison.core.mcp.config import configure_mcp_json

    warning: Optional[str] = None

    try:
        result = configure_mcp_json(
            project_root=project_root,
            prefer_scripts=use_script,
            dry_run=False,
        )
        added = result.get("_meta", {}).get("added")
        if added:
            formatter.text("✅ Configured .mcp.json with managed servers")
        else:
            formatter.text("ℹ️  MCP servers already configured in .mcp.json")
        return True, warning
    except Exception as exc:
        warning = f"⚠️  Warning: Could not configure .mcp.json: {exc}"
        formatter.text(warning)
        formatter.text("   Run 'edison mcp configure' manually.")
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
        pal=False,
        dry_run=False,
        json=False,
        repo_root=str(project_root),
    )

    compose_all.main(args)


def _run_questionnaire(
    project_root: Path,
    mode: str,
    formatter: OutputFormatter,
    force: bool = False,
    merge: bool = False,
    interactive: bool = True,
    provided_answers: Optional[dict] = None,
) -> bool:
    """Run the setup questionnaire and write config files.
    
    Args:
        project_root: Repository root path
        mode: 'basic' or 'advanced'
        formatter: Output formatter
        force: Overwrite existing files
        merge: Merge with existing files
        
    Returns:
        True if successful, False otherwise
    """
    from edison.core.setup import configure_project, WriteMode
    
    # Determine write mode
    if force:
        write_mode = WriteMode.OVERWRITE
    elif merge:
        write_mode = WriteMode.MERGE
    else:
        write_mode = WriteMode.CREATE
    
    # Run questionnaire with file writing enabled
    result = configure_project(
        repo_root=project_root,
        interactive=interactive,
        mode=mode,
        provided_answers=provided_answers,
        write_files=True,
        write_mode=write_mode,
        overrides_only=True,  # Only write values that differ from defaults
    )
    
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        formatter.text(f"❌ Configuration failed: {error}")
        return False
    
    # Report what was written
    write_result = result.get("write_result")
    if write_result:
        if write_result.files_written:
            formatter.text("\n📝 Config files written:")
            for path in write_result.files_written:
                formatter.text(f"   - {path.name}")
        
        if write_result.files_merged:
            formatter.text("\n🔄 Config files merged:")
            for path in write_result.files_merged:
                formatter.text(f"   - {path.name}")
        
        if write_result.files_skipped:
            formatter.text("\n⏭️  Existing files skipped (use --force or --merge):")
            for path in write_result.files_skipped:
                formatter.text(f"   - {path.name}")
        
        if write_result.errors:
            formatter.text("\n❌ Errors:")
            for error in write_result.errors:
                formatter.text(f"   - {error}")
            return False
    
    return True


def _print_banner(formatter: OutputFormatter, project_name: str, reconfigure: bool = False) -> None:
    """Print the setup banner."""
    action = "Reconfiguring" if reconfigure else "Initializing"
    formatter.text(f"\n{'='*60}")
    formatter.text(f"  Edison Project Setup - {action}")
    formatter.text(f"  Project: {project_name}")
    formatter.text(f"{'='*60}\n")


def _print_next_steps(formatter: OutputFormatter, config_root: Path) -> None:
    """Print next steps after initialization."""
    formatter.text("\n✅ Edison initialized successfully!")
    formatter.text("\nNext steps:")
    formatter.text(f"  1. Review {config_root.name}/config/*.yml for your overrides")
    formatter.text("  2. Run 'edison compose all' to regenerate artifacts after changes")
    formatter.text("  3. Start a session: edison session create [--session-id <id>]")


def main(args: argparse.Namespace) -> int:
    """Initialize Edison in the given project directory."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    # E2E tests may invoke init.main() with a partial argparse.Namespace. Normalize
    # missing options to their CLI defaults so main() remains robust.
    defaults: dict[str, object] = {
        "advanced": False,
        "force": False,
        "merge": False,
        "reconfigure": False,
        "non_interactive": False,
        "skip_mcp": False,
        "mcp_script": False,
        "skip_compose": False,
        "enable_worktrees": False,
        "disable_worktrees": False,
        "skip_worktree_meta_init": False,
    }
    for key, value in defaults.items():
        if not hasattr(args, key):
            setattr(args, key, value)

    project_root = Path(args.project_path).expanduser().resolve()

    # CI / subprocess safety: if stdin is not interactive, default to non-interactive
    # mode unless the user explicitly requested otherwise.
    if not getattr(args, "non_interactive", False):
        try:
            if not sys.stdin.isatty():
                args.non_interactive = True
        except Exception:
            args.non_interactive = True
    
    # Check if already initialized
    config_root = get_project_config_dir(project_root, create=False)
    already_initialized = config_root.exists() and (config_root / "config").exists()
    
    # Validate reconfigure flag
    if args.reconfigure and not already_initialized:
        formatter.text("❌ Cannot reconfigure: Project not initialized yet.")
        formatter.text("   Run 'edison init' first without --reconfigure.")
        return 1
    
    # For non-reconfigure on existing project, warn
    if already_initialized and not args.reconfigure and not args.force and not args.merge:
        formatter.text(f"ℹ️  Project already initialized at {config_root}")
        formatter.text("   Use --reconfigure to update configuration")
        formatter.text("   Use --force to overwrite existing files")
        formatter.text("   Use --merge to merge with existing files")
        return 0
    
    try:
        project_name = project_root.name
        _print_banner(formatter, project_name, reconfigure=args.reconfigure)
        
        # Create structure (idempotent)
        config_root = _ensure_structure(project_root)
        _copy_mcp_scripts(config_root)
        formatter.text(f"✅ Created {config_root} structure")

        # Fail closed: --mcp-script requires run-server.sh to exist in the project.
        # This is only available when Edison is running from a source checkout that
        # includes `scripts/pal/` (unless the package distribution bundles them).
        if getattr(args, "mcp_script", False):
            run_script = config_root / "scripts" / "pal" / "run-server.sh"
            if not run_script.exists():
                formatter.text("❌ --mcp-script requested but Pal run script is not available.")
                formatter.text(f"   Missing: {run_script}")
                formatter.text("   Recommended: use default uvx-based setup (omit --mcp-script).")
                formatter.text("   Or install Edison from a source checkout that includes scripts/pal.")
                return 1
        
        if getattr(args, "enable_worktrees", False) and getattr(args, "disable_worktrees", False):
            formatter.text("❌ --enable-worktrees and --disable-worktrees are mutually exclusive.")
            return 1

        # Determine mode (basic / advanced)
        mode = "advanced" if args.advanced else "basic"

        provided_answers: dict = {}
        if getattr(args, "enable_worktrees", False):
            provided_answers["enable_worktrees"] = True
        if getattr(args, "disable_worktrees", False):
            provided_answers["enable_worktrees"] = False

        if args.non_interactive:
            formatter.text("\n📋 Non-interactive mode: writing recommended defaults (no prompts)")
        else:
            formatter.text(f"\n📋 Running setup questionnaire ({mode} mode)...")
            formatter.text("   Press Enter to accept defaults shown in [brackets]\n")

        success = _run_questionnaire(
            project_root,
            mode=mode,
            formatter=formatter,
            force=args.force,
            merge=args.merge,
            interactive=not args.non_interactive,
            provided_answers=provided_answers or None,
        )
        if not success:
            return 1

        # If worktrees are enabled and meta mode is active, bootstrap the meta worktree now
        # (idempotent). This ensures sharedPaths symlinks + per-worktree excludes + meta commit
        # guard are installed before we run composition, so generated artifacts land in the
        # shared/meta root.
        if not getattr(args, "skip_worktree_meta_init", False):
            try:
                from edison.core.config import ConfigManager
                from edison.core.session import worktree as wt

                cfg = ConfigManager(project_root).load_config(validate=False, include_packs=True) or {}
                wt_cfg = cfg.get("worktrees") or {}
                ss = wt_cfg.get("sharedState") or {}
                if wt_cfg.get("enabled") and str(ss.get("mode") or "meta").strip().lower() == "meta":
                    formatter.text("\n🌿 Initializing worktrees shared-state meta worktree...")
                    wt.initialize_meta_shared_state(repo_dir=project_root, dry_run=False)
            except Exception as exc:
                formatter.text(f"❌ Worktree meta init failed: {exc}")
                formatter.text("   You can re-run later via: edison git worktree-meta-init")
                return 1
        
        # Configure MCP
        if not args.skip_mcp:
            formatter.text("")
            _configure_mcp(project_root, use_script=args.mcp_script, formatter=formatter)
        else:
            formatter.text("\nℹ️  Skipped MCP setup (--skip-mcp)")

        # Run composition (after meta init so shared dirs exist + are symlinked)
        if not args.skip_compose:
            formatter.text("\n🔧 Running initial composition...")
            _run_initial_composition(project_root)
        else:
            formatter.text("\nℹ️  Skipped composition (--skip-compose)")
        
        _print_next_steps(formatter, config_root)
        return 0

    except KeyboardInterrupt:
        formatter.text("\n\n⚠️  Setup cancelled by user.")
        return 130
    except Exception as exc:
        formatter.error(exc, error_code="init_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
