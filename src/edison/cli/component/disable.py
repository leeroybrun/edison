from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag

from ._shared import formatter, resolve_kind_and_id, service

SUMMARY = "Disable a component (pack/validator/adapter/agent)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("kind_or_id", help="Component kind (or id for alias domains)")
    parser.add_argument("id", nargs="?", help="Component id")
    add_repo_root_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    out = formatter(args)
    try:
        kind, cid = resolve_kind_and_id(args, kind_or_id=args.kind_or_id, component_id=args.id)
        svc = service(args)
        toggle = svc.disable(kind, cid)
        if out.json_mode:
            out.json_output(
                {
                    "kind": kind,
                    "id": cid,
                    "enabled": False,
                    "configPath": str(toggle.config_path),
                }
            )
        else:
            out.text(f"Disabled {kind} {cid} (wrote {toggle.config_path.name})")
        return 0
    except Exception as exc:
        out.error(exc, error_code="component_disable_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))
