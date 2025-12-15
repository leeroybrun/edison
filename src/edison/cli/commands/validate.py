"""Edison validate command.

SUMMARY: Validate a structured report file against its schema.

Canonical report format is Markdown with YAML frontmatter.
Canonical schema format is YAML (JSON Schema expressed in YAML).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa.evidence.report_io import read_structured_report
from edison.core.schemas.validation import validate_payload_safe

SUMMARY = "Validate a structured report file (implementation/validator)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", help="Path to report file (.md with YAML frontmatter)")
    parser.add_argument(
        "--schema",
        choices=["auto", "implementation-report", "validator-report"],
        default="auto",
        help="Schema to validate against (default: auto-detect from filename)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _detect_schema(path: Path) -> Optional[str]:
    name = path.name.lower()
    if name.startswith("implementation-report."):
        return "reports/implementation-report.schema.yaml"
    if name.startswith("validator-") and "-report." in name:
        return "reports/validator-report.schema.yaml"
    return None


def _label_for_schema(schema_name: str) -> str:
    if schema_name.endswith("implementation-report.schema.yaml"):
        return "Implementation report"
    if schema_name.endswith("validator-report.schema.yaml"):
        return "Validator report"
    return "Report"


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    repo_root = get_repo_root(args)

    path = Path(str(args.path))
    if not path.exists():
        formatter.error(f"File not found: {path}", error_code="not_found")
        return 1
    if path.suffix.lower() not in {".md", ".markdown"}:
        formatter.error("Report must be Markdown (.md) with YAML frontmatter", error_code="invalid_extension")
        return 1

    schema_choice = str(getattr(args, "schema", "auto"))
    if schema_choice == "implementation-report":
        schema_name = "reports/implementation-report.schema.yaml"
    elif schema_choice == "validator-report":
        schema_name = "reports/validator-report.schema.yaml"
    else:
        schema_name = _detect_schema(path) or ""

    if not schema_name:
        formatter.error(
            "Unable to auto-detect schema for this file; pass --schema.",
            error_code="schema_unknown",
        )
        return 2

    payload = read_structured_report(path)
    if not payload:
        formatter.error("Missing or invalid YAML frontmatter payload", error_code="invalid_payload")
        return 3

    errors = validate_payload_safe(payload, schema_name, repo_root=repo_root)
    label = _label_for_schema(schema_name)

    if errors:
        if formatter.json_mode:
            formatter.json_output(
                {
                    "ok": False,
                    "schema": schema_name,
                    "label": label,
                    "errors": errors,
                    "path": str(path),
                }
            )
        else:
            formatter.text("Schema errors:")
            for e in errors:
                formatter.text(f"- {e}")
        return 1

    if formatter.json_mode:
        formatter.json_output({"ok": True, "schema": schema_name, "label": label, "path": str(path)})
    else:
        formatter.text(f"{label} valid")
    return 0
