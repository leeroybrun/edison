from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag

from ._shared import formatter, is_interactive, parse_kv_pairs, resolve_kind_and_id, service

SUMMARY = "Configure a component using its setup spec"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("kind_or_id", help="Component kind (or id for alias domains)")
    parser.add_argument("id", nargs="?", help="Component id")
    parser.add_argument(
        "--mode",
        choices=["basic", "advanced"],
        default="basic",
        help="Question mode for setup specs (basic|advanced)",
    )
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help="Provide setup question answer as KEY=VALUE (repeatable)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail instead of prompting when required answers are missing",
    )
    add_repo_root_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    out = formatter(args)
    try:
        kind, cid = resolve_kind_and_id(args, kind_or_id=args.kind_or_id, component_id=args.id)
        svc = service(args)
        answers = parse_kv_pairs(getattr(args, "answer", []))
        wrote = svc.configure(
            kind,
            cid,
            interactive=is_interactive(args),
            provided_answers=answers,
            mode=str(args.mode),
        )
        status = svc.get_status(kind, cid)
        if out.json_mode:
            out.json_output(
                {
                    "kind": kind,
                    "id": cid,
                    "written": [str(p) for p in wrote],
                    "missingRequiredConfig": status.missing_required_config,
                }
            )
        else:
            if wrote:
                for p in wrote:
                    out.text(f"Wrote {p.name}")
            else:
                out.text("No setup spec found; no changes written.")
            if status.missing_required_config:
                out.text("Missing required config:")
                for p in status.missing_required_config:
                    out.text(f"  - {p}")
        return 0
    except Exception as exc:
        out.error(exc, error_code="component_configure_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))
