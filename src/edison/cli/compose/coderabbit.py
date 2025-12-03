"""
Edison compose coderabbit command.

SUMMARY: Compose CodeRabbit configuration from Edison config
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.adapters import CoderabbitAdapter

SUMMARY = "Compose CodeRabbit configuration from Edison config"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for .coderabbit.yaml file",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose CodeRabbit configuration - delegates to composition engine."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        adapter = CoderabbitAdapter(project_root=repo_root)

        if args.dry_run:
            # Compose config but don't write
            coderabbit_config = adapter.compose_coderabbit_config()

            if args.json:
                formatter.json_output({
                    "status": "dry-run",
                    "repo_root": str(repo_root),
                    "config": coderabbit_config,
                })
            else:
                formatter.text(f"[dry-run] Would compose CodeRabbit config from {repo_root}")
                import yaml
                formatter.text("\nConfiguration preview:")
                formatter.text(yaml.dump(coderabbit_config, default_flow_style=False))
            return 0

        # Determine output path
        output_path = Path(args.output) if args.output else None

        # Write configuration
        written_path = adapter.write_coderabbit_config(output_path=output_path)

        if args.json:
            formatter.json_output({
                "status": "success",
                "config_file": str(written_path),
            })
        else:
            formatter.text(f"Composed CodeRabbit configuration:")
            formatter.text(f"  - {written_path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="compose_coderabbit_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
