"""
Edison task bundle add command.

SUMMARY: Add tasks to a validation bundle (set bundle_root)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Add tasks to a validation bundle (set bundle_root)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        required=True,
        help="Bundle root task id (validation runs at this root)",
    )
    parser.add_argument(
        "members",
        nargs="+",
        help="Member task ids to add to the bundle (each will point bundle_root -> root)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing bundle_root relationship on a member task",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        root_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.root))

        from edison.core.task.relationships.service import TaskRelationshipService
        from edison.core.qa.bundler.cluster import select_cluster

        member_ids: list[str] = []
        for raw in list(getattr(args, "members", []) or []):
            mid = resolve_existing_task_id(project_root=project_root, raw_task_id=str(raw))
            if mid == root_id:
                raise ValueError("A task cannot be a bundle member of itself")
            member_ids.append(mid)

        svc = TaskRelationshipService(project_root=project_root)
        for mid in sorted(set(member_ids)):
            svc.add(task_id=mid, rel_type="bundle_root", target_id=root_id, force=bool(getattr(args, "force", False)))

        selection = select_cluster(root_id, scope="bundle", project_root=project_root)
        cluster_ids = list(selection.task_ids)
        members = [t for t in cluster_ids if t != selection.root_task_id]

        payload = {
            "status": "updated",
            "rootTask": str(selection.root_task_id),
            "members": members,
            "count": len(members),
        }
        if formatter.json_mode:
            # Include bundle guidance (shared with `edison qa bundle`) so agents
            # learn the expected workflow at the moment they create the bundle.
            from edison.core.qa.bundler import build_validation_manifest
            from edison.core.qa.workflow.next_steps import build_bundle_next_steps_payload

            manifest = build_validation_manifest(
                str(selection.root_task_id),
                scope="bundle",
                project_root=project_root,
                session_id=None,
            )
            guidance = build_bundle_next_steps_payload(manifest=manifest, project_root=project_root)
            payload.update(
                {
                    "nextSteps": guidance.get("nextSteps") or [],
                    "bundleReports": guidance.get("bundleReports") or {},
                }
            )
            formatter.json_output(payload)
        else:
            from edison.core.qa.bundler import build_validation_manifest
            from edison.core.qa.workflow.next_steps import build_bundle_next_steps_payload, format_bundle_next_steps_text

            manifest = build_validation_manifest(
                str(selection.root_task_id),
                scope="bundle",
                project_root=project_root,
                session_id=None,
            )
            guidance = build_bundle_next_steps_payload(manifest=manifest, project_root=project_root)
            formatter.text(
                f"Bundle root: {selection.root_task_id}\n"
                f"Members ({len(members)}): " + (", ".join(members) if members else "(none)") + "\n\n"
                + format_bundle_next_steps_text(guidance)
            )
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="task_bundle_add_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
