"""
Edison config show command.

SUMMARY: Show current configuration

Displays the merged configuration from bundled defaults, project overrides,
and environment variables. Supports filtering by key and multiple output formats.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.config import ConfigManager

SUMMARY = "Show current configuration"

def _nest_key(key: str, value):
    """Nest a dot-notation key into a YAML/JSON-friendly mapping."""
    parts = [p for p in str(key).split(".") if p]
    out = value
    for part in reversed(parts):
        out = {part: out}
    return out


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "key",
        nargs="?",
        help="Specific configuration key to show (e.g., 'project.name')",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "table"],
        default="table",
        help="Output format (default: table)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _format_value(value, indent: int = 0) -> str:
    """Format a value for table display."""
    prefix = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            formatted = _format_value(v, indent + 1)
            if "\n" in formatted:
                lines.append(f"{prefix}{k}:")
                lines.append(formatted)
            else:
                lines.append(f"{prefix}{k}: {formatted}")
        return "\n".join(lines)
    elif isinstance(value, list):
        if not value:
            return "[]"
        if all(isinstance(v, (str, int, float, bool)) for v in value):
            return f"[{', '.join(str(v) for v in value)}]"
        lines = []
        for v in value:
            formatted = _format_value(v, indent + 1)
            lines.append(f"{prefix}- {formatted}")
        return "\n".join(lines)
    else:
        return str(value)


def main(args: argparse.Namespace) -> int:
    """Show configuration - delegates to ConfigManager."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        config_manager = ConfigManager(repo_root)

        output_format = "json" if args.json else args.format

        # Handle specific key lookup
        if args.key:
            value = config_manager.get(args.key)
            if value is None:
                formatter.text(f"Key not found: {args.key}")
                return 1

            if output_format == "json":
                formatter.json_output({args.key: value})
            elif output_format == "yaml":
                try:
                    import yaml

                    # Emit YAML as nested mapping so dot-notation keys remain readable.
                    formatter.text(
                        yaml.safe_dump(
                            _nest_key(args.key, value),
                            default_flow_style=False,
                            sort_keys=True,
                            allow_unicode=True,
                        ).rstrip()
                    )
                except ImportError:
                    formatter.text("PyYAML not installed, falling back to JSON")
                    formatter.json_output({args.key: value})
            else:
                formatted = _format_value(value, indent=1)
                formatter.text(f"{args.key}:")
                formatter.text(formatted)
            return 0

        # Get full merged config
        config_data = config_manager.get_all()

        # Handle full config display
        if output_format == "json":
            formatter.json_output(config_data)
        elif output_format == "yaml":
            try:
                import yaml
                formatter.text(
                    yaml.safe_dump(
                        config_data,
                        default_flow_style=False,
                        sort_keys=True,
                        allow_unicode=True,
                    ).rstrip()
                )
            except ImportError:
                formatter.text("PyYAML not installed, falling back to JSON")
                formatter.json_output(config_data)
        else:  # table format
            formatter.text("Edison Configuration")
            formatter.text("=" * 60)
            formatter.text("")
            
            # Show key sections with better formatting
            priority_sections = ["project", "paths", "packs", "database", "worktrees"]
            shown = set()
            
            for section in priority_sections:
                if section in config_data:
                    shown.add(section)
                    formatter.text(f"[{section}]")
                    value = config_data[section]
                    if isinstance(value, dict):
                        for k, v in value.items():
                            formatted = _format_value(v, 1)
                            if "\n" in formatted:
                                formatter.text(f"  {k}:")
                                for line in formatted.split("\n"):
                                    formatter.text(f"  {line}")
                            else:
                                formatter.text(f"  {k}: {formatted}")
                    else:
                        formatter.text(f"  {_format_value(value)}")
                    formatter.text("")
            
            # Show remaining sections
            remaining = sorted(set(config_data.keys()) - shown)
            if remaining:
                formatter.text("--- Other Settings ---")
                formatter.text("")
                for section in remaining:
                    formatter.text(f"[{section}]")
                    value = config_data[section]
                    if isinstance(value, dict):
                        for k, v in value.items():
                            formatted = _format_value(v, 1)
                            if len(str(formatted)) > 60:
                                formatter.text(f"  {k}: <complex>")
                            else:
                                formatter.text(f"  {k}: {formatted}")
                    else:
                        formatter.text(f"  {_format_value(value)}")
                    formatter.text("")

        return 0

    except Exception as e:
        formatter.error(e, error_code="config_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
