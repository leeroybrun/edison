"""
Edison session context command.

SUMMARY: Print a deterministic project/session context refresher (hook-safe)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_format_flag, add_json_flag, add_repo_root_flag, get_repo_root, resolve_output_format, resolve_session_id

SUMMARY = "Print a deterministic project/session context refresher (hook-safe)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Optional session identifier (defaults to auto-detected current session)",
    )
    add_format_flag(parser, default="markdown")
    add_json_flag(parser)  # Backwards compatibility
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    output_format = resolve_output_format(args)
    formatter = OutputFormatter(format=output_format)

    try:
        project_root = get_repo_root(args)

        from edison.core.session.context_payload import (
            build_session_context_payload,
            format_session_context_markdown,
        )

        # IMPORTANT: Determine whether this is an Edison project BEFORE attempting
        # session auto-resolution, because session detection may create `.edison/`
        # directories via low-level path helpers. Hooks must be safe no-ops in
        # non-Edison repos.
        base_payload = build_session_context_payload(project_root=project_root, session_id=None)
        if not base_payload.is_edison_project:
            payload = base_payload
        else:
            session_id = resolve_session_id(
                project_root=project_root,
                explicit=getattr(args, "session_id", None),
                required=False,
            )
            payload = build_session_context_payload(project_root=project_root, session_id=session_id)

        if formatter.json_mode:
            formatter.json_output(payload.to_dict())
        else:
            text = format_session_context_markdown(payload)
            if text:
                # Optional: append long-term memory hits (config-driven, fail-open).
                try:
                    from edison.core.config import ConfigManager
                    from edison.core.memory import MemoryManager

                    full = ConfigManager(repo_root=project_root).load_config(
                        validate=False, include_packs=True
                    )
                    mem = full.get("memory", {}) if isinstance(full.get("memory", {}), dict) else {}
                    inj = (
                        mem.get("contextInjection", {})
                        if isinstance(mem.get("contextInjection", {}), dict)
                        else {}
                    )

                    if (
                        bool(mem.get("enabled", False))
                        and bool(inj.get("enabled", False))
                        and payload.session_id
                    ):
                        limit_raw = inj.get("limit", 0)
                        limit = int(limit_raw) if limit_raw is not None else 0
                        limit = None if limit <= 0 else limit

                        tmpl = str(inj.get("queryTemplate") or "{session_id}")
                        query = tmpl.format(
                            session_id=payload.session_id or "",
                            current_task_id=payload.current_task_id or "",
                            current_task_state=payload.current_task_state or "",
                            project_root=str(project_root),
                        ).strip()

                        if query:
                            mgr = MemoryManager(project_root=project_root)
                            hits = mgr.search(query, limit=limit)
                            if hits:
                                heading = str(inj.get("heading") or "## Memory Hits")
                                max_chars = int(inj.get("maxCharsPerHit", 800))
                                max_chars = 0 if max_chars < 0 else max_chars

                                extra: list[str] = []
                                extra.append("")
                                extra.append(heading)
                                extra.append("")
                                for h in hits:
                                    ht = (h.text or "").strip()
                                    if max_chars and len(ht) > max_chars:
                                        ht = ht[:max_chars].rstrip() + "…"
                                    extra.append(f"- ({h.provider_id}) {ht}")
                                extra.append("")

                                text = text.rstrip() + "\n" + "\n".join(extra)
                except Exception:
                    pass

                formatter.text(text)
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="context_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
