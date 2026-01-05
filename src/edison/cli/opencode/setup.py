"""
Edison OpenCode setup command.

SUMMARY: Generate project-local OpenCode plugin artifacts for Edison
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import (
    OutputFormatter,
    add_dry_run_flag,
    add_force_flag,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
)
from edison.core.utils.io import ensure_directory, write_text
from edison.core.utils.text import render_template_text
from edison.data import read_text as data_read_text
from edison.data import read_yaml as data_read_yaml

SUMMARY = "Generate project-local OpenCode plugin artifacts for Edison"


def _get_opencode_config() -> dict:
    """Load OpenCode configuration from YAML."""
    return data_read_yaml("config", "opencode.yaml").get("opencode", {})


def _get_agent_templates() -> list[str]:
    """Get agent template names from config."""
    cfg = _get_opencode_config()
    return list(cfg.get("agentTemplates", []))


def _get_command_templates() -> list[str]:
    """Get command template names from config."""
    cfg = _get_opencode_config()
    return list(cfg.get("commandTemplates", []))


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply changes without interactive confirmation (still requires --force to overwrite modified files)",
    )
    parser.add_argument(
        "--agents",
        action="store_true",
        help="Generate OpenCode agent definitions under .opencode/agent/",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        help="Generate OpenCode command definitions under .opencode/command/",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all OpenCode artifacts (plugin, agents, commands, config, deps)",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Generate opencode.json project config in repo root",
    )
    parser.add_argument(
        "--plugin-deps",
        action="store_true",
        help="Generate .opencode/package.json for plugin dependencies",
    )
    add_force_flag(parser)
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _is_edison_project(repo_root: Path) -> bool:
    # Minimal, deterministic check (no legacy `.edison/core` paths).
    return (repo_root / ".edison" / "config").exists()


def _render_plugin_template(*, repo_root: Path) -> str:
    template = data_read_text("templates", "opencode/plugin/edison.ts.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _render_agent_template(name: str, *, repo_root: Path) -> str:
    """Render an agent template by name."""
    template = data_read_text("templates", f"opencode/agent/{name}.md.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _render_command_template(name: str, *, repo_root: Path) -> str:
    """Render a command template by name."""
    template = data_read_text("templates", f"opencode/command/{name}.md.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _compute_change(target: Path, desired: str) -> dict[str, str]:
    """Compute the change action for a target file."""
    exists = target.exists()
    current = target.read_text(encoding="utf-8") if exists else ""
    needs_write = (not exists) or (current != desired)
    action = "create" if not exists else ("noop" if not needs_write else "update")
    return {"path": str(target), "action": action, "current": current, "desired": desired}


def _collect_plugin_changes(repo_root: Path) -> list[dict[str, str]]:
    """Collect changes for the plugin."""
    target = repo_root / ".opencode" / "plugin" / "edison.ts"
    desired = _render_plugin_template(repo_root=repo_root)
    return [_compute_change(target, desired)]


def _collect_agent_changes(repo_root: Path) -> list[dict[str, str]]:
    """Collect changes for all agent files."""
    changes = []
    agent_dir = repo_root / ".opencode" / "agent"
    for name in _get_agent_templates():
        target = agent_dir / f"{name}.md"
        desired = _render_agent_template(name, repo_root=repo_root)
        changes.append(_compute_change(target, desired))
    return changes


def _collect_command_changes(repo_root: Path) -> list[dict[str, str]]:
    """Collect changes for all command files."""
    changes = []
    cmd_dir = repo_root / ".opencode" / "command"
    for name in _get_command_templates():
        target = cmd_dir / f"{name}.md"
        desired = _render_command_template(name, repo_root=repo_root)
        changes.append(_compute_change(target, desired))
    return changes


def _render_config_template(*, repo_root: Path) -> str:
    """Render the opencode.json config template."""
    template = data_read_text("templates", "opencode/opencode.json.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _render_schema_template() -> str:
    """Render the vendored OpenCode JSON schema (static)."""
    return data_read_text("templates", "opencode/schema/opencode-config.schema.json")


def _render_package_template(*, repo_root: Path) -> str:
    """Render the .opencode/package.json template."""
    template = data_read_text("templates", "opencode/package.json.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _collect_config_changes(repo_root: Path) -> list[dict[str, str]]:
    """Collect changes for opencode.json config."""
    target = repo_root / "opencode.json"
    desired = _render_config_template(repo_root=repo_root)
    return [_compute_change(target, desired)]


def _collect_schema_changes(repo_root: Path) -> list[dict[str, str]]:
    """Collect changes for vendored OpenCode JSON schema."""
    target = repo_root / ".opencode" / "schema" / "opencode-config.schema.json"
    desired = _render_schema_template()
    return [_compute_change(target, desired)]


def _collect_plugin_deps_changes(repo_root: Path) -> list[dict[str, str]]:
    """Collect changes for .opencode/package.json."""
    target = repo_root / ".opencode" / "package.json"
    desired = _render_package_template(repo_root=repo_root)
    return [_compute_change(target, desired)]


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        if not _is_edison_project(repo_root):
            raise RuntimeError(f"Not an Edison project: missing {repo_root / '.edison' / 'config'}")

        # Determine what to generate based on flags
        gen_all = bool(getattr(args, "all", False))
        gen_agents = gen_all or bool(getattr(args, "agents", False))
        gen_commands = gen_all or bool(getattr(args, "commands", False))
        gen_config = gen_all or bool(getattr(args, "config", False))
        gen_plugin_deps = gen_all or bool(getattr(args, "plugin_deps", False))
        # Plugin is always generated unless only specific flags are specified
        explicit_flags = gen_agents or gen_commands or gen_config or gen_plugin_deps
        gen_plugin = gen_all or not explicit_flags

        # Collect all changes
        all_changes: list[dict[str, str]] = []
        if gen_plugin:
            all_changes.extend(_collect_plugin_changes(repo_root))
        if gen_agents:
            all_changes.extend(_collect_agent_changes(repo_root))
        if gen_commands:
            all_changes.extend(_collect_command_changes(repo_root))
        if gen_config:
            all_changes.extend(_collect_config_changes(repo_root))
            all_changes.extend(_collect_schema_changes(repo_root))
        if gen_plugin_deps:
            all_changes.extend(_collect_plugin_deps_changes(repo_root))

        # Filter to only changes that need writing (for output)
        changes_for_output = [
            {"path": c["path"], "action": c["action"]}
            for c in all_changes
        ]
        changes_needing_write = [c for c in all_changes if c["action"] != "noop"]

        # Dry run - just report what would happen
        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "changes": changes_for_output})
            else:
                formatter.text("[dry-run] Would ensure OpenCode artifacts exist:")
                for c in changes_for_output:
                    formatter.text(f"  - {c['action']}: {c['path']}")
            return 0

        # Check if nothing needs writing
        if not changes_needing_write:
            if args.json:
                formatter.json_output({"status": "ok", "changes": changes_for_output})
            else:
                formatter.text("OpenCode artifacts already up to date.")
            return 0

        # Check for blocked overwrites (modified files without --force)
        force = bool(getattr(args, "force", False))
        blocked = []
        for c in changes_needing_write:
            if c["action"] == "update" and c["current"] != c["desired"] and not force:
                blocked.append(c["path"])

        if blocked:
            if args.json:
                formatter.json_output({
                    "status": "blocked",
                    "error": "Target files differ; refuse to overwrite without --force",
                    "paths": blocked,
                })
            else:
                formatter.text("Refusing to overwrite modified files without --force:")
                for p in blocked:
                    formatter.text(f"  - {p}")
                formatter.text("Re-run with `--force --yes` to overwrite.")
            return 1

        # Require --yes to apply changes
        if not bool(getattr(args, "yes", False)):
            if args.json:
                formatter.json_output({
                    "status": "confirm",
                    "changes": changes_for_output,
                    "note": "Re-run with --yes to apply",
                })
            else:
                formatter.text("Planned changes:")
                for c in changes_for_output:
                    if c["action"] != "noop":
                        formatter.text(f"  - {c['action']}: {c['path']}")
                formatter.text("Re-run with `--yes` to apply.")
            return 1

        # Apply all changes
        for c in changes_needing_write:
            target = Path(c["path"])
            ensure_directory(target.parent)
            write_text(target, c["desired"])

        if args.json:
            formatter.json_output({"status": "ok", "changes": changes_for_output})
        else:
            formatter.text("Wrote OpenCode artifacts:")
            for c in changes_needing_write:
                formatter.text(f"  - {c['action']}: {c['path']}")
            formatter.text("OpenCode will auto-discover project-local artifacts.")

        return 0

    except Exception as e:
        formatter.error(e, error_code="opencode_setup_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))
