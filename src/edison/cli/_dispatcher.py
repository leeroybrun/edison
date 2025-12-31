"""
Auto-discovery CLI dispatcher for Edison.

Scans subfolders for commands and automatically registers them.
Adding new commands = just add a .py file to the appropriate subfolder.

Rules Integration:
- Rules with CLI configuration are displayed before/after command execution
- Configure rules in data/rules/registry.yml with cli.commands and cli.timing
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

from edison.cli._aliases import domain_cli_names, resolve_canonical_domain
from edison.core.utils.profiling import Profiler, enable_profiler, span


@lru_cache(maxsize=1)
def discover_domains() -> dict[str, Path]:
    """
    Discover all CLI domain subfolders (session, task, config, etc.).

    Returns:
        Dict mapping domain name to directory path
    """
    cli_dir = Path(__file__).parent
    domains = {}
    for item in cli_dir.iterdir():
        if item.name == "commands":
            continue
        if item.is_dir() and not item.name.startswith("_"):
            # Must have at least one non-init .py file
            has_commands = any(
                f.suffix == ".py" and not f.name.startswith("_")
                for f in item.iterdir()
            )
            if has_commands:
                domains[item.name] = item
    return domains


@lru_cache(maxsize=32)
def discover_root_commands() -> dict[str, dict[str, Any]]:
    """Discover top-level commands under cli/commands (no domain prefix)."""

    with span("cli.discover.root_commands"):
        cli_dir = Path(__file__).parent
        commands_dir = cli_dir / "commands"
    commands: dict[str, dict[str, Any]] = {}

    if not commands_dir.exists():
        return commands

    for item in commands_dir.glob("*.py"):
        if item.name.startswith("_"):
            continue

        cmd_name = item.stem
        try:
            with span("cli.discover.import", module=f"edison.cli.commands.{cmd_name}"):
                module = importlib.import_module(f"edison.cli.commands.{cmd_name}")
            commands[cmd_name] = {
                "module": module,
                "summary": getattr(module, "SUMMARY", cmd_name),
                "register_args": getattr(module, "register_args", None),
                "main": getattr(module, "main", None),
            }
        except ImportError as e:
            print(f"Warning: Could not import command {cmd_name}: {e}", file=sys.stderr)
            continue

    return commands


@lru_cache(maxsize=32)
def discover_commands(domain: str) -> dict[str, dict[str, Any]]:
    """
    Discover all commands in a domain subfolder.

    Args:
        domain: Name of the domain (e.g., "session", "task")

    Returns:
        Dict mapping command name to command info dict
    """
    with span("cli.discover.domain_commands", domain=domain):
        cli_dir = Path(__file__).parent
        domain_dir = cli_dir / domain
    commands: dict[str, dict[str, Any]] = {}

    for item in domain_dir.glob("*.py"):
        if item.name.startswith("_"):
            continue

        cmd_name = item.stem
        try:
            # Import module and get metadata
            with span("cli.discover.import", module=f"edison.cli.{domain}.{cmd_name}"):
                module = importlib.import_module(f"edison.cli.{domain}.{cmd_name}")
            commands[cmd_name] = {
                "module": module,
                "summary": getattr(module, "SUMMARY", f"{domain} {cmd_name}"),
                "register_args": getattr(module, "register_args", None),
                "main": getattr(module, "main", None),
            }
        except ImportError as e:
            # Skip modules with import errors (will be caught during actual use)
            print(f"Warning: Could not import {domain}.{cmd_name}: {e}", file=sys.stderr)
            continue

    return commands


@lru_cache(maxsize=32)
def discover_command_groups(domain: str) -> dict[str, dict[str, Any]]:
    """Discover command groups under a domain (one level deep).

    Example:
        cli/session/recovery/*.py => `edison session recovery <subcommand>`
        cli/session/db/*.py       => `edison session db <subcommand>`

    Returns:
        Dict mapping group name -> dict with:
          - summary: group help text
          - commands: subcommand mapping (same shape as discover_commands())
    """
    with span("cli.discover.domain_command_groups", domain=domain):
        cli_dir = Path(__file__).parent
        domain_dir = cli_dir / domain

    groups: dict[str, dict[str, Any]] = {}
    if not domain_dir.exists():
        return groups

    for subdir in domain_dir.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        init_py = subdir / "__init__.py"
        if not init_py.exists():
            continue

        try:
            with span("cli.discover.import", module=f"edison.cli.{domain}.{subdir.name}"):
                pkg = importlib.import_module(f"edison.cli.{domain}.{subdir.name}")
            summary = (getattr(pkg, "__doc__", "") or "").strip().splitlines()[0] if getattr(pkg, "__doc__", None) else ""
        except ImportError as e:
            print(f"Warning: Could not import {domain}.{subdir.name} group: {e}", file=sys.stderr)
            continue

        subcommands: dict[str, dict[str, Any]] = {}
        for item in subdir.glob("*.py"):
            if item.name.startswith("_") or item.name == "__init__.py":
                continue
            cmd_name = item.stem
            try:
                with span(
                    "cli.discover.import",
                    module=f"edison.cli.{domain}.{subdir.name}.{cmd_name}",
                ):
                    module = importlib.import_module(f"edison.cli.{domain}.{subdir.name}.{cmd_name}")
                subcommands[cmd_name] = {
                    "module": module,
                    "summary": getattr(module, "SUMMARY", f"{domain} {subdir.name} {cmd_name}"),
                    "register_args": getattr(module, "register_args", None),
                    "main": getattr(module, "main", None),
                }
            except ImportError as e:
                print(
                    f"Warning: Could not import {domain}.{subdir.name}.{cmd_name}: {e}",
                    file=sys.stderr,
                )
                continue

        if subcommands:
            groups[subdir.name] = {"summary": summary or f"{subdir.name} commands", "commands": subcommands}

    return groups


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser with auto-discovered domains and commands.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="edison",
        description="Edison Framework - AI-automated project management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Emit profiling information for CLI discovery, config loading, and command execution (sent to stderr).",
    )

    subparsers = parser.add_subparsers(
        dest="domain",
        title="domains",
        description="Available command domains",
        metavar="<domain>",
    )

    # Register top-level commands (no domain prefix)
    for cmd_name, cmd_info in sorted(discover_root_commands().items()):
        primary_name = cmd_name.replace("_", "-")
        aliases = [cmd_name] if primary_name != cmd_name else []
        cmd_parser = subparsers.add_parser(
            primary_name,
            aliases=aliases,
            help=cmd_info["summary"],
        )
        if cmd_info["register_args"]:
            cmd_info["register_args"](cmd_parser)
        if cmd_info["main"]:
            cmd_parser.set_defaults(_func=cmd_info["main"])

    # Auto-register domains
    for domain_name in sorted(discover_domains().keys()):
        domain_commands = discover_commands(domain_name)
        domain_groups = discover_command_groups(domain_name)
        if not domain_commands:
            if not domain_groups:
                continue

        # Create domain parser
        domain_primary, domain_aliases = domain_cli_names(domain_name)
        domain_parser = subparsers.add_parser(
            domain_primary,
            aliases=domain_aliases,
            help=f"{domain_primary.title()} management commands",
        )
        cmd_subparsers = domain_parser.add_subparsers(
            dest="command",
            title="commands",
            description=f"Available {domain_primary} commands",
            metavar="<command>",
        )

        # Auto-register commands in domain
        for cmd_name, cmd_info in sorted(domain_commands.items()):
            primary_name = cmd_name.replace("_", "-")
            aliases = [cmd_name] if primary_name != cmd_name else []
            cmd_parser = cmd_subparsers.add_parser(
                primary_name,
                aliases=aliases,
                help=cmd_info["summary"],
            )

            # Let module register its own arguments
            if cmd_info["register_args"]:
                cmd_info["register_args"](cmd_parser)

            # Set the main function as default handler
            if cmd_info["main"]:
                cmd_parser.set_defaults(_func=cmd_info["main"])

        # Auto-register one-level command groups (domain/<group>/<subcommand>.py)
        for group_name, group_info in sorted(domain_groups.items()):
            group_primary = group_name.replace("_", "-")
            group_aliases = [group_name] if group_primary != group_name else []
            group_parser = cmd_subparsers.add_parser(
                group_primary,
                aliases=group_aliases,
                help=group_info.get("summary") or f"{group_name} commands",
            )
            group_subparsers = group_parser.add_subparsers(
                dest="subcommand",
                title="subcommands",
                description=f"Available {domain_name} {group_name} subcommands",
                metavar="<subcommand>",
            )

            for subcmd_name, subcmd_info in sorted((group_info.get("commands") or {}).items()):
                sub_primary = subcmd_name.replace("_", "-")
                sub_aliases = [subcmd_name] if sub_primary != subcmd_name else []
                sub_parser = group_subparsers.add_parser(
                    sub_primary,
                    aliases=sub_aliases,
                    help=subcmd_info.get("summary") or f"{domain_name} {group_name} {subcmd_name}",
                )
                if subcmd_info.get("register_args"):
                    subcmd_info["register_args"](sub_parser)
                if subcmd_info.get("main"):
                    sub_parser.set_defaults(_func=subcmd_info["main"])

    return parser


def _get_version() -> str:
    """Get Edison version string."""
    try:
        from edison import __version__
        return __version__
    except ImportError:
        return "unknown"


def _get_rules_engine() -> Any | None:
    """Get RulesEngine instance for rules display.

    Returns None if rules engine cannot be initialized (e.g., not in project).
    """
    try:
        from edison.core.config import ConfigManager
        from edison.core.rules import RulesEngine
        cfg = ConfigManager().load_config(validate=False)
        return RulesEngine(cfg)
    except Exception:
        return None


def _get_active_packs_fast(project_root: Path) -> list[str]:
    """Fast active pack detection for CLI rules display.

    Avoids a full ConfigManager load when we only need `packs.active`.
    """
    try:
        from edison.core.utils.io import read_yaml
        from edison.core.utils.paths import get_project_config_dir

        cfg_root = get_project_config_dir(project_root, create=False)
        cfg_dir = cfg_root / "config"

        cfg_path = cfg_dir / "packs.yml"
        if not cfg_path.exists():
            cfg_path = cfg_dir / "packs.yaml"
        if not cfg_path.exists():
            return []
        data = read_yaml(cfg_path, default={}) or {}
        packs = (data.get("packs") or {}).get("active") if isinstance(data, dict) else None
        if isinstance(packs, list):
            return [str(p) for p in packs if p]
        return []
    except Exception:
        return []


def _path_within(child: Path, parent: Path) -> bool:
    try:
        c = child.resolve()
        p = parent.resolve()
        return c == p or c.is_relative_to(p)
    except Exception:
        return False


def _extract_session_id_from_args(args: argparse.Namespace) -> str | None:
    # Common patterns across commands:
    # - positional `session_id`
    # - optional `--session`
    # - explicit `--id`/`--session-id` (stored as session_id)
    for key in ("session_id", "session", "id", "sessionId"):
        try:
            val = getattr(args, key, None)
        except Exception:
            val = None
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _extract_task_id_from_args(args: argparse.Namespace) -> str | None:
    # Prefer explicit task_id fields used by QA/validation commands.
    raw = getattr(args, "task_id", None)
    if raw:
        return str(raw)

    # Many task commands use a positional `record_id` that can refer to either a task or a QA record.
    record_id = getattr(args, "record_id", None)
    if record_id:
        try:
            from edison.cli._utils import detect_record_type

            if detect_record_type(str(record_id)) != "task":
                return None
        except Exception:
            return None

        try:
            from edison.core.task import normalize_record_id

            return normalize_record_id("task", str(record_id))
        except Exception:
            return str(record_id)

    return None


def _is_mutating_invocation(command_name: str, args: argparse.Namespace) -> bool:
    """Best-effort classification of whether a CLI invocation mutates project state.

    This is used to make worktree enforcement safe-by-default:
    - Read-only invocations should be allowed from the primary checkout.
    - Mutating invocations should be blocked unless run inside the session worktree.
    """
    # Standard pattern: many commands expose a dry-run mode.
    if bool(getattr(args, "dry_run", False)):
        return False

    # session status: read-only unless transitioning.
    if command_name == "session status":
        return bool(getattr(args, "status", None))

    # task status: read-only unless transitioning.
    if command_name == "task status":
        return bool(getattr(args, "status", None))

    # task split: read-only on dry-run, mutating otherwise.
    if command_name == "task split":
        return True

    # qa validate: roster-only/dry-run are read-only. Execution/check-only writes evidence.
    if command_name == "qa validate":
        if bool(getattr(args, "check_only", False)):
            return True
        return bool(getattr(args, "execute", False))

    # qa run: dry-run is read-only, execution writes evidence.
    if command_name == "qa run":
        return True

    # qa promote: dry-run is read-only, execution transitions QA state.
    if command_name == "qa promote":
        return True

    # session validate: currently read-only unless explicitly tracking scores.
    if command_name == "session validate":
        return bool(getattr(args, "track_scores", False))

    # session track: only "active" is read-only; others write tracking artifacts.
    if command_name == "session track":
        sub = str(getattr(args, "subcommand", "") or "")
        return sub in {"start", "heartbeat", "complete"}

    # session next / verify are read-only by design.
    if command_name in {"session next", "session verify"}:
        return False

    # Default for known-mutating commands (no dry-run).
    if command_name in {
        "session close",
        "session complete",
        "task claim",
        "task mark-delegated",
        "task link",
        "qa bundle",
    }:
        return True

    # Fallback: if a command exposes a `status` parameter and it is set, treat as mutating.
    if getattr(args, "status", None):
        return True

    # Conservative default: treat unknown commands in the enforcement list as mutating.
    return True


def _maybe_enforce_session_worktree(
    *,
    project_root: Path,
    command_name: str,
    args: argparse.Namespace,
    json_mode: bool,
) -> int | None:
    """Return an exit code when enforcement blocks the command, else None."""
    try:
        from edison.cli._worktree_enforcement import maybe_enforce_session_worktree

        return maybe_enforce_session_worktree(
            project_root=project_root,
            command_name=command_name,
            args=args,
            json_mode=json_mode,
        )
    except Exception:
        return None


def _get_cli_rules_to_display(
    *,
    project_root: Path,
    rules_map: dict[str, dict[str, Any]],
    command_name: str,
    timing: str,
) -> list[dict[str, Any]]:
    """Filter CLI-displayable rules from an already-composed rules map."""

    out: list[dict[str, Any]] = []
    for rule in rules_map.values():
        if not isinstance(rule, dict):
            continue
        cli_cfg = rule.get("cli") or {}
        if not isinstance(cli_cfg, dict):
            continue
        commands = cli_cfg.get("commands") or []
        if not isinstance(commands, list) or not commands:
            continue
        if command_name not in commands and "*" not in commands:
            continue
        rule_timing = str(cli_cfg.get("timing") or "before")
        if timing != "both" and rule_timing != "both" and rule_timing != timing:
            continue

        out.append(
            {
                "id": rule.get("id"),
                "title": rule.get("title") or rule.get("id"),
                "blocking": bool(rule.get("blocking", False)),
                "body": rule.get("body") or "",
            }
        )

    return out


def _registry_has_cli_rules_for_command(
    registry: dict[str, Any],
    *,
    command_name: str,
    timing: str,
) -> bool:
    """Fast scan of a raw YAML registry dict for any CLI-displayable rule."""
    raw_rules = registry.get("rules") or []
    if not isinstance(raw_rules, list):
        return False

    for rule in raw_rules:
        if not isinstance(rule, dict):
            continue
        cli_cfg = rule.get("cli") or {}
        if not isinstance(cli_cfg, dict):
            continue
        commands = cli_cfg.get("commands") or []
        if not isinstance(commands, list) or not commands:
            continue
        if command_name not in commands and "*" not in commands:
            continue
        rule_timing = str(cli_cfg.get("timing") or "before")
        if timing != "both" and rule_timing != "both" and rule_timing != timing:
            continue
        return True
    return False


def _format_rules_for_display(rules: list[dict[str, Any]], timing: str) -> str:
    """Format rules for CLI display.

    Args:
        rules: List of composed rule dicts
        timing: "before" or "after"

    Returns:
        Formatted string for display
    """
    if not rules:
        return ""

    header = "RULES TO FOLLOW:" if timing == "before" else "VALIDATION REMINDERS:"
    lines = [f"\n{'='*60}", f"📋 {header}", ""]

    for rule in rules:
        blocking_marker = "[BLOCKING] " if rule.get("blocking") else ""
        lines.append(f"  {blocking_marker}{rule.get('title', rule.get('id', 'Unknown'))}")
        content = rule.get("body") or rule.get("content")
        if content:
            # Show first 200 chars of content
            snippet = content[:200]
            if len(content) > 200:
                snippet += "..."
            for line in snippet.split("\n")[:3]:
                if line.strip():
                    lines.append(f"    {line.strip()}")
        lines.append("")

    lines.append("=" * 60 + "\n")
    return "\n".join(lines)


def _strip_profile_flag(argv: list[str]) -> tuple[list[str], bool]:
    """Strip the global profiling flag only when it appears before the domain.

    The top-level `--profile` flag enables internal CLI profiling spans and
    takes no value. Subcommands may legitimately define their own `--profile`
    options (e.g. orchestrator profile selection). To avoid collisions, we only
    treat `--profile` as the global profiling flag when it appears before the
    first non-flag token (the domain).
    """
    if not argv:
        return argv, False
    enabled = False
    out: list[str] = []

    # Identify the domain position: first argument that does not look like a flag.
    domain_index: int | None = None
    for i, a in enumerate(argv):
        if not a.startswith("-"):
            domain_index = i
            break

    for i, a in enumerate(argv):
        if a == "--profile" and (domain_index is None or i < domain_index):
            enabled = True
            continue
        out.append(a)
    return out, enabled


def _is_help_requested(argv: list[str]) -> bool:
    return any(a in ("-h", "--help") for a in argv)


def _resolve_fast_command_module(argv: list[str]) -> dict[str, str] | None:
    """Resolve the target command module without importing all CLI commands.

    This enables a fast path for normal command invocations where we only import
    the one command module the user is running.

    Returns:
        Dict with keys: module, domain, command, command_name
        - module: import path (e.g., edison.cli.rules.check)
        - domain: domain name or "" for root command
        - command: command name (cli form, e.g. "check")
        - command_name: full command name (e.g., "rules check" or "compose-all")
    """
    if not argv:
        return None
    if argv[0].startswith("-"):
        return None

    cli_dir = Path(__file__).parent
    domains = discover_domains()

    # Domain command: `edison <domain> <command> ...`
    resolved_domain = resolve_canonical_domain(argv[0], canonical_domains=tuple(domains.keys()))
    if resolved_domain:
        if len(argv) < 2 or argv[1].startswith("-"):
            return None
        domain = resolved_domain
        cmd_cli = argv[1]
        cmd_mod = cmd_cli.replace("-", "_")
        candidate = cli_dir / domain / f"{cmd_mod}.py"
        if not candidate.exists():
            return None
        return {
            "module": f"edison.cli.{domain}.{cmd_mod}",
            "domain": domain,
            "command": cmd_cli,
            "command_name": f"{domain} {cmd_cli}",
        }

    # Root command: `edison <command> ...` (module lives under cli/commands/)
    cmd_cli = argv[0]
    cmd_mod = cmd_cli.replace("-", "_")
    candidate = cli_dir / "commands" / f"{cmd_mod}.py"
    if not candidate.exists():
        return None
    return {
        "module": f"edison.cli.commands.{cmd_mod}",
        "domain": "",
        "command": cmd_cli,
        "command_name": cmd_cli,
    }


def _build_fast_parser(spec: dict[str, str]) -> argparse.ArgumentParser:
    """Build an argparse parser for only the resolved command (fast path)."""
    with span("cli.version.get"):
        version = _get_version()
    with span("cli.fast.parser.init"):
        parser = argparse.ArgumentParser(
            prog="edison",
            description="Edison Framework - AI-automated project management",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version}",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Emit profiling information for CLI discovery, config loading, and command execution (sent to stderr).",
    )

    with span("cli.fast.parser.subparsers"):
        subparsers = parser.add_subparsers(dest="domain")

    # Import only the target module.
    with span("cli.fast.import", module=spec["module"]):
        module = importlib.import_module(spec["module"])

    register_args = getattr(module, "register_args", None)
    main_func = getattr(module, "main", None)
    summary = getattr(module, "SUMMARY", spec["command_name"])

    with span("cli.fast.parser.register"):
        if spec["domain"]:
            domain_primary, domain_aliases = domain_cli_names(spec["domain"])
            domain_parser = subparsers.add_parser(
                domain_primary,
                aliases=domain_aliases,
                help=f"{domain_primary.title()} management commands",
            )
            cmd_subparsers = domain_parser.add_subparsers(dest="command")
            primary_name = spec["command"].replace("_", "-")
            cmd_parser = cmd_subparsers.add_parser(primary_name, help=summary)
            if register_args:
                register_args(cmd_parser)
            if main_func:
                cmd_parser.set_defaults(_func=main_func)
        else:
            primary_name = spec["command"].replace("_", "-")
            cmd_parser = subparsers.add_parser(primary_name, help=summary)
            if register_args:
                register_args(cmd_parser)
            if main_func:
                cmd_parser.set_defaults(_func=main_func)

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for Edison CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    if argv is None:
        argv = sys.argv[1:]

    argv, profile_enabled = _strip_profile_flag(list(argv))

    profiler = Profiler() if profile_enabled else None
    ctx = enable_profiler(profiler) if profiler else None
    if ctx is None:
        from contextlib import nullcontext
        ctx = nullcontext()

    result: int
    with ctx:
        with span("cli.total"):
            help_requested = _is_help_requested(argv)
            spec = None if help_requested else _resolve_fast_command_module(argv)

            if spec is not None:
                with span("cli.parser.build_fast"):
                    parser = _build_fast_parser(spec)
            else:
                with span("cli.parser.build_full"):
                    parser = build_parser()
            with span("cli.parser.parse_args"):
                args = parser.parse_args(argv)

            # If no domain specified, show help
            if not args.domain:
                parser.print_help()
                return 0

            # If no command specified and no handler bound, show domain help
            if not getattr(args, "command", None) and not getattr(args, "_func", None):
                # Re-parse with just the domain to get its help
                domain_parser = parser._subparsers._group_actions[0].choices.get(args.domain)
                if domain_parser:
                    domain_parser.print_help()
                return 0

            # Get command name for rules lookup
            domains = discover_domains()
            canonical_domain = resolve_canonical_domain(
                args.domain,
                canonical_domains=tuple(domains.keys()),
            )
            command_name = canonical_domain or args.domain
            if getattr(args, "command", None):
                command_name = f"{command_name} {args.command}"

            audit_repo_root = None
            try:
                # Prefer explicit `--repo-root` when present; fall back to auto-detection.
                from edison.cli._utils import get_repo_root

                audit_repo_root = get_repo_root(args)
            except Exception:
                audit_repo_root = None

            from contextlib import nullcontext

            result = 1
            session_id = _extract_session_id_from_args(args)
            task_id = _extract_task_id_from_args(args)
            if session_id is None and audit_repo_root is not None:
                try:
                    from edison.core.session.core.id import detect_session_id

                    session_id = detect_session_id(project_root=audit_repo_root)
                except Exception:
                    session_id = None
            if audit_repo_root is not None:
                try:
                    from edison.core.audit import audit_invocation

                    inv_cm = audit_invocation(
                        argv=list(argv),
                        command_name=command_name,
                        repo_root=audit_repo_root,
                        session_id=session_id,
                        task_id=task_id,
                    )
                except Exception:
                    inv_cm = nullcontext()
            else:
                inv_cm = nullcontext()

            with inv_cm as inv:
                # Rules commands manage rules themselves; avoid double-initializing the rules engine
                # (dispatcher guidance + rules CLI) which is expensive and redundant.
                project_root = None
                if args.domain != "rules":
                    try:
                        from edison.core.utils.paths import PathResolver

                        project_root = PathResolver.resolve_project_root()
                    except Exception:
                        project_root = None

                # Compose rules once per CLI invocation (core + packs + project) for CLI display.
                # This avoids loading full config and avoids composing twice for before/after.
                rules_map: dict[str, dict[str, Any]] = {}
                if project_root is not None:
                    try:
                        from edison.core.rules.registry import RulesRegistry

                        packs = _get_active_packs_fast(project_root)
                        registry = RulesRegistry(project_root=project_root)
                        with span("cli.rules.compose", packs=len(packs)):
                            composed = registry.compose_cli_rules_for_command(
                                packs=packs,
                                command_name=command_name,
                                resolve_sources=False,
                            )
                        rules_map = composed.get("rules", {}) if isinstance(composed, dict) else {}
                        if not isinstance(rules_map, dict):
                            rules_map = {}
                    except Exception:
                        rules_map = {}

                # Show BEFORE rules (guidance)
                json_mode = bool(getattr(args, "json", False))
                if json_mode:
                    # JSON mode must remain machine-readable (stdout/stderr should not be polluted
                    # by logging warnings emitted via the stdlib "lastResort" handler).
                    try:
                        from edison.core.audit.stdlib_logging import (
                            suppress_lastresort_in_json_mode,
                        )

                        suppress_lastresort_in_json_mode()
                    except Exception:
                        pass
                if project_root is not None and not json_mode:
                    try:
                        with span("cli.rules.get", timing="before"):
                            before_rules = _get_cli_rules_to_display(
                                project_root=project_root,
                                rules_map=rules_map,
                                command_name=command_name,
                                timing="before",
                            )
                        if before_rules:
                            print(_format_rules_for_display(before_rules, "before"), file=sys.stderr)
                    except Exception:
                        pass  # Fail silently - rules display is optional

                # Execute the command
                func: Callable[[argparse.Namespace], int] | None = getattr(args, "_func", None)
                if func:
                    try:
                        if project_root is not None:
                            blocked = _maybe_enforce_session_worktree(
                                project_root=project_root,
                                command_name=command_name,
                                args=args,
                                json_mode=json_mode,
                            )
                            if blocked is not None:
                                result = blocked
                                if inv is not None:
                                    try:
                                        inv.set_exit_code(result)
                                    except Exception:
                                        pass
                                return result
                        with span("cli.command.exec", command=command_name):
                            result = func(args)
                    except KeyboardInterrupt:
                        print("\nInterrupted.", file=sys.stderr)
                        result = 130
                        if inv is not None:
                            try:
                                inv.set_exit_code(result)
                            except Exception:
                                pass
                        return result
                    except Exception as e:
                        print(f"Error: {e}", file=sys.stderr)
                        result = 1
                        if inv is not None:
                            try:
                                inv.set_exit_code(result)
                            except Exception:
                                pass
                        return result
                else:
                    parser.print_help()
                    result = 1
                    if inv is not None:
                        try:
                            inv.set_exit_code(result)
                        except Exception:
                            pass
                    return result

                # Show AFTER rules (validation reminders) - only on success
                if project_root is not None and result == 0 and not json_mode:
                    try:
                        with span("cli.rules.get", timing="after"):
                            after_rules = _get_cli_rules_to_display(
                                project_root=project_root,
                                rules_map=rules_map,
                                command_name=command_name,
                                timing="after",
                            )
                        if after_rules:
                            print(_format_rules_for_display(after_rules, "after"), file=sys.stderr)
                    except Exception:
                        pass  # Fail silently - rules display is optional

                if inv is not None:
                    try:
                        inv.set_exit_code(result)
                    except Exception:
                        pass
                return result

    if profiler is not None:
        totals = profiler.summary_ms()
        top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:50]
        print("\nProfiling (top spans):", file=sys.stderr)
        for name, ms in top:
            print(f"- {name}: {ms:.1f}ms", file=sys.stderr)

    return result


if __name__ == "__main__":
    sys.exit(main())
