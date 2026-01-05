from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag

from ._shared import formatter, resolve_kind_and_id, service, status_payload

SUMMARY = "Show component status (enabled/required config)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("kind_or_id", nargs="?", help="Component kind (or id for alias domains)")
    parser.add_argument("id", nargs="?", help="Component id")
    add_repo_root_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    out = formatter(args)
    try:
        svc = service(args)

        if args.kind_or_id and args.id:
            kind, cid = resolve_kind_and_id(args, kind_or_id=args.kind_or_id, component_id=args.id)
            status = svc.get_status(kind, cid)
            if out.json_mode:
                out.json_output(status_payload(status))
            else:
                out.text(f"{kind} {cid}: {'ENABLED' if status.enabled else 'DISABLED'}")
                if not status.available:
                    out.text("  - not available in this project")
                if status.missing_required_config:
                    out.text("  - missing required config:")
                    for p in status.missing_required_config:
                        out.text(f"    - {p}")
            return 0

        # Kind-only (or alias domain with no id): list all statuses for that kind.
        if args.kind_or_id and not args.id:
            # Could be `component status <kind>` OR `pack status <id>`.
            try:
                kind, cid = resolve_kind_and_id(args, kind_or_id=args.kind_or_id, component_id=None)
                # Alias domain: treat arg as id.
                status = svc.get_status(kind, cid)
                if out.json_mode:
                    out.json_output(status_payload(status))
                else:
                    out.text(f"{kind} {cid}: {'ENABLED' if status.enabled else 'DISABLED'}")
                    if status.missing_required_config:
                        out.text("  - missing required config:")
                        for p in status.missing_required_config:
                            out.text(f"    - {p}")
                return 0
            except ValueError:
                # `component status <kind>`
                kind = str(args.kind_or_id).strip()
                if kind not in {"pack", "validator", "adapter", "agent"}:
                    raise
                payload = []
                for cid in svc.list_available(kind):  # type: ignore[arg-type]
                    payload.append(status_payload(svc.get_status(kind, cid)))  # type: ignore[arg-type]
                if out.json_mode:
                    out.json_output({"kind": kind, "items": payload})
                else:
                    out.text(f"{kind}s: {len(payload)}")
                    for item in payload[:50]:
                        enabled = bool(item.get("enabled"))
                        out.text(
                            f"  - {item.get('component_id')}: {'ENABLED' if enabled else 'DISABLED'}"
                        )
                    if len(payload) > 50:
                        out.text(f"  ... and {len(payload) - 50} more")
                return 0

        # No args: show all kinds.
        payload = {}
        for kind in ("pack", "validator", "adapter", "agent"):
            payload[kind] = [
                status_payload(svc.get_status(kind, cid)) for cid in svc.list_available(kind)
            ]  # type: ignore[arg-type]
        if out.json_mode:
            out.json_output(payload)
        else:
            for kind in ("pack", "validator", "adapter", "agent"):
                enabled_count = sum(1 for i in payload[kind] if i.get("enabled"))
                out.text(f"{kind}s: {enabled_count}/{len(payload[kind])} enabled")
        return 0
    except Exception as exc:
        out.error(exc, error_code="component_status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))
