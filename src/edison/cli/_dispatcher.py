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
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
        if not domain_commands:
            continue

        # Create domain parser
        domain_parser = subparsers.add_parser(
            domain_name,
            help=f"{domain_name.title()} management commands",
        )
        cmd_subparsers = domain_parser.add_subparsers(
            dest="command",
            title="commands",
            description=f"Available {domain_name} commands",
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

    return parser


def _get_version() -> str:
    """Get Edison version string."""
    try:
        from edison import __version__
        return __version__
    except ImportError:
        return "unknown"


def _get_rules_engine() -> Optional[Any]:
    """Get RulesEngine instance for rules display.
    
    Returns None if rules engine cannot be initialized (e.g., not in project).
    """
    try:
        from edison.core.rules import RulesEngine
        from edison.core.config import ConfigManager
        cfg = ConfigManager().load_config(validate=False)
        return RulesEngine(cfg)
    except Exception:
        return None


def _get_active_packs_fast(project_root: Path) -> List[str]:
    """Fast active pack detection for CLI rules display.

    Avoids a full ConfigManager load when we only need `packs.active`.
    """
    try:
        from edison.core.utils.io import read_yaml

        cfg_path = project_root / ".edison" / "config" / "packs.yml"
        if not cfg_path.exists():
            cfg_path = project_root / ".edison" / "config" / "packs.yaml"
        if not cfg_path.exists():
            return []
        data = read_yaml(cfg_path, default={}) or {}
        packs = (data.get("packs") or {}).get("active") if isinstance(data, dict) else None
        if isinstance(packs, list):
            return [str(p) for p in packs if p]
        return []
    except Exception:
        return []


def _get_cli_rules_to_display(
    *,
    project_root: Path,
    rules_map: Dict[str, Dict[str, Any]],
    command_name: str,
    timing: str,
) -> List[Dict[str, Any]]:
    """Filter CLI-displayable rules from an already-composed rules map."""

    out: List[Dict[str, Any]] = []
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
    registry: Dict[str, Any],
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


def _format_rules_for_display(rules: List[Dict[str, Any]], timing: str) -> str:
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
    """Allow `--profile` anywhere in argv (before or after subcommands)."""
    if not argv:
        return argv, False
    enabled = False
    out: list[str] = []
    for a in argv:
        if a == "--profile":
            enabled = True
            continue
        out.append(a)
    return out, enabled


def _is_help_requested(argv: list[str]) -> bool:
    return any(a in ("-h", "--help") for a in argv)


def _resolve_fast_command_module(argv: list[str]) -> Optional[dict[str, str]]:
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
    if argv[0] in domains:
        if len(argv) < 2 or argv[1].startswith("-"):
            return None
        domain = argv[0]
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
            domain_parser = subparsers.add_parser(
                spec["domain"],
                help=f"{spec['domain'].title()} management commands",
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
            command_name = args.domain
            if getattr(args, "command", None):
                command_name = f"{args.domain} {args.command}"

            # Rules commands manage rules themselves; avoid double-initializing the rules engine
            # (dispatcher guidance + rules CLI) which is expensive and redundant.
            engine = None
            project_root = None
            if args.domain != "rules":
                try:
                    from edison.core.utils.paths import PathResolver

                    project_root = PathResolver.resolve_project_root()
                except Exception:
                    project_root = None

            # Compose rules once per CLI invocation (core + packs + project) for CLI display.
            # This avoids loading full config and avoids composing twice for before/after.
            rules_map: Dict[str, Dict[str, Any]] = {}
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
            if project_root is not None:
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
            result = 1
            if func:
                try:
                    with span("cli.command.exec", command=command_name):
                        result = func(args)
                except KeyboardInterrupt:
                    print("\nInterrupted.", file=sys.stderr)
                    return 130
                except Exception as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1
            else:
                parser.print_help()
                return 1

            # Show AFTER rules (validation reminders) - only on success
            if project_root is not None and result == 0:
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

    if profiler is not None:
        totals = profiler.summary_ms()
        top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:50]
        print("\nProfiling (top spans):", file=sys.stderr)
        for name, ms in top:
            print(f"- {name}: {ms:.1f}ms", file=sys.stderr)

    return result


if __name__ == "__main__":
    sys.exit(main())
