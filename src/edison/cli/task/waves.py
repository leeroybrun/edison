"""
Edison task waves command.

SUMMARY: Compute topological "waves" of parallelizable todo tasks from depends_on
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root, resolve_session_id

SUMMARY = 'Compute topological "waves" of parallelizable todo tasks from depends_on'


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--session",
        help="Optional session scope for planning (filters to tasks with matching session_id)",
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=None,
        help="Optional max parallel cap override (defaults to orchestration.maxConcurrentAgents when available)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        session_id = (
            resolve_session_id(project_root=project_root, explicit=args.session, required=False)
            if args.session
            else None
        )

        from edison.core.task.planning import TaskPlanner

        plan = TaskPlanner(project_root=project_root).build_plan(session_id=session_id)
        payload = plan.to_dict()
        payload["session_id"] = session_id
        payload["wave_count"] = len(payload.get("waves", []))
        payload["blocked_count"] = len(payload.get("blocked", []))

        # Optional delegation cap guidance (defense-in-depth for orchestrators).
        max_concurrent: int | None = None
        if getattr(args, "cap", None) is not None:
            max_concurrent = int(args.cap)
        else:
            try:
                from edison.core.config.domains.qa import QAConfig

                max_concurrent = QAConfig(repo_root=project_root).get_max_concurrent_validators()
            except Exception:
                max_concurrent = None

        payload["maxConcurrentAgents"] = max_concurrent
        payload["maxConcurrent"] = max_concurrent  # compatibility alias for consumers

        if max_concurrent and payload.get("waves"):
            batches: list[dict[str, object]] = []
            for w in payload["waves"]:
                tasks = list(w.get("tasks", [])) if isinstance(w, dict) else []
                if not tasks:
                    continue
                wave_no = int(w.get("wave", 0) or 0)
                total_batches = (len(tasks) + max_concurrent - 1) // max_concurrent
                for i in range(total_batches):
                    start = i * max_concurrent
                    end = start + max_concurrent
                    batches.append(
                        {
                            "wave": wave_no,
                            "batch": i + 1,
                            "batchesInWave": total_batches,
                            "cap": max_concurrent,
                            "tasks": tasks[start:end],
                        }
                    )
            payload["batches"] = batches

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            if payload["waves"]:
                lines: list[str] = []
                if max_concurrent:
                    lines.append(f"Max concurrent: {max_concurrent}")
                for w in payload["waves"]:
                    ids = [t["id"] for t in w.get("tasks", [])]
                    lines.append(f"Wave {w.get('wave')}: {', '.join(ids)}")
                batches = payload.get("batches", [])
                if max_concurrent and isinstance(batches, list):
                    multi = [
                        b
                        for b in batches
                        if (b or {}).get("batchesInWave", 1)
                        and int((b or {}).get("batchesInWave", 1) or 1) > 1
                    ]
                    if multi:
                        lines.append("\nBatch suggestions (respect cap):")
                        shown = 0
                        for b in multi:
                            if shown >= 25:
                                lines.append(f"  ... and {len(multi) - shown} more (use --json for full list)")
                                break
                            tasks = b.get("tasks", [])
                            ids = [t.get("id") for t in tasks if isinstance(t, dict) and t.get("id")]
                            lines.append(
                                f"  - Wave {b.get('wave')} batch {b.get('batch')}/{b.get('batchesInWave')}: "
                                f"{', '.join(ids)}"
                            )
                            shown += 1
                if payload["blocked"]:
                    lines.append(f"\nBlocked ({payload['blocked_count']}):")
                    for b in payload["blocked"][:25]:
                        lines.append(f"  - {b.get('id')}: {b.get('title', '')}")
                formatter.text("\n".join(lines))
            else:
                if payload["blocked"]:
                    formatter.text(
                        f"No schedulable todo tasks (blocked: {payload['blocked_count']}). "
                        "Use --json for details."
                    )
                else:
                    formatter.text("No schedulable todo tasks.")

        return 0
    except Exception as exc:
        formatter.error(exc, error_code="waves_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

