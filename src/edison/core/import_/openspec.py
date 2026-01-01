"""OpenSpec import module for Edison.

Imports OpenSpec *change folders* as Edison tasks ("thin" tasks with links).

Design: 1 Edison task per OpenSpec change (by change-id). OpenSpec's tasks.md
checkboxes do not have stable IDs, so task-level syncing is intentionally out of
scope for this importer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from edison.core.entity import EntityMetadata
from edison.core.import_.sync import SyncResult, sync_items_to_tasks
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository
from edison.core.utils.paths import safe_relpath


class OpenSpecImportError(Exception):
    """Error during OpenSpec import operation."""


@dataclass(frozen=True)
class OpenSpecSource:
    """Resolved OpenSpec source paths."""

    repo_root: Path
    openspec_dir: Path
    changes_dir: Path


@dataclass(frozen=True)
class OpenSpecChange:
    """An OpenSpec change folder."""

    change_id: str
    change_dir: Path
    proposal_path: Path
    tasks_path: Path
    specs_dir: Path
    design_path: Path


def parse_openspec_source(source: Path) -> OpenSpecSource:
    """Resolve an OpenSpec source path to canonical repo/openspec/changes paths.

    Accepts:
    - <repo-root> (contains openspec/)
    - <repo-root>/openspec
    - <repo-root>/openspec/changes
    """
    src = Path(source)
    if not src.exists():
        raise OpenSpecImportError(f"Source not found: {src}")

    # Normalize common entry points.
    if src.is_dir() and src.name == "changes" and src.parent.name == "openspec":
        repo_root = src.parent.parent
        openspec_dir = src.parent
        changes_dir = src
    elif src.is_dir() and src.name == "openspec":
        repo_root = src.parent
        openspec_dir = src
        changes_dir = openspec_dir / "changes"
    else:
        repo_root = src
        openspec_dir = repo_root / "openspec"
        changes_dir = openspec_dir / "changes"

    if not openspec_dir.is_dir():
        raise OpenSpecImportError("openspec directory not found")
    if not changes_dir.is_dir():
        raise OpenSpecImportError("openspec changes directory not found")

    return OpenSpecSource(
        repo_root=repo_root,
        openspec_dir=openspec_dir,
        changes_dir=changes_dir,
    )


def list_openspec_changes(
    src: OpenSpecSource, *, include_archived: bool = False
) -> List[OpenSpecChange]:
    """List OpenSpec change folders."""
    changes: List[OpenSpecChange] = []
    for entry in sorted(src.changes_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name == "archive" and not include_archived:
            continue
        if entry.name == "archive" and include_archived:
            # Archive entries are nested: changes/archive/YYYY-MM-DD-change-id
            for archived in sorted(entry.iterdir()):
                if not archived.is_dir():
                    continue
                maybe = _try_parse_change_dir(archived)
                if maybe:
                    changes.append(maybe)
            continue

        maybe = _try_parse_change_dir(entry)
        if maybe:
            changes.append(maybe)

    changes.sort(key=lambda c: c.change_id)
    return changes


def _try_parse_change_dir(change_dir: Path) -> Optional[OpenSpecChange]:
    proposal = change_dir / "proposal.md"
    if not proposal.exists():
        return None
    return OpenSpecChange(
        change_id=change_dir.name,
        change_dir=change_dir,
        proposal_path=proposal,
        tasks_path=change_dir / "tasks.md",
        specs_dir=change_dir / "specs",
        design_path=change_dir / "design.md",
    )


def generate_edison_task_from_openspec_change(
    change: OpenSpecChange,
    *,
    prefix: str,
    project_root: Path,
) -> Task:
    task_id = f"{prefix}-{change.change_id}"
    title = _extract_title_from_proposal(change.proposal_path, fallback=change.change_id)

    description = _render_task_description(change, project_root=project_root)

    tags = ["openspec", prefix, "openspec-change"]
    return Task(
        id=task_id,
        state="todo",
        title=title,
        description=description,
        tags=tags,
        integration={
            "kind": "openspec",
            "openspec": {
                "change_id": change.change_id,
                "change_dir": safe_relpath(change.change_dir, project_root=project_root),
                "proposal_md": safe_relpath(change.proposal_path, project_root=project_root),
                "tasks_md": safe_relpath(change.tasks_path, project_root=project_root),
                "design_md": safe_relpath(change.design_path, project_root=project_root),
            },
        },
        metadata=EntityMetadata.create(created_by="openspec-import"),
    )


def _extract_title_from_proposal(path: Path, *, fallback: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip() or fallback
    except Exception:
        return fallback
    return fallback


def _render_task_description(change: OpenSpecChange, *, project_root: Path) -> str:
    def rel(p: Path) -> str:
        return safe_relpath(p, project_root=project_root)

    lines: List[str] = [
        f"**OpenSpec Change**: `{rel(change.change_dir)}`",
        "",
        "## Workflow (MUST FOLLOW)",
        "1. Confirm the change proposal is approved before implementation.",
        "2. Read **Required Reading** below before editing code.",
        "3. Implement the checklist in `tasks.md` sequentially; only mark items `- [x]` after they are truly complete.",
        "4. Edison will attempt to sync source checkboxes when the task is marked `validated` (configurable).",
        "",
        "## Required Reading (MUST)",
        f"- `{rel(change.proposal_path)}`",
    ]
    if change.design_path.exists():
        lines.append(f"- `{rel(change.design_path)}`")
    if change.tasks_path.exists():
        lines.append(f"- `{rel(change.tasks_path)}`")
    if change.specs_dir.exists():
        lines.append(f"- `{rel(change.specs_dir)}/`")

    lines.extend(
        [
            "",
            "## Useful Commands",
            f"- `openspec validate {change.change_id} --strict`",
            f"- `openspec show {change.change_id} --json --deltas-only`",
        ]
    )
    return "\n".join(lines).rstrip()


def sync_openspec_changes(
    src: OpenSpecSource,
    *,
    prefix: str = "openspec",
    create_qa: bool = True,
    dry_run: bool = False,
    include_archived: bool = False,
    project_root: Optional[Path] = None,
) -> SyncResult:
    """Import/sync OpenSpec changes into Edison tasks.

    Matching is by OpenSpec change-id -> Edison task id `{prefix}-{change-id}`.
    """
    repo_root = project_root or src.repo_root
    changes = list_openspec_changes(src, include_archived=include_archived)
    task_repo = TaskRepository(repo_root)

    def _update_task(task: Task, change: OpenSpecChange) -> None:
        updated = generate_edison_task_from_openspec_change(
            change, prefix=prefix, project_root=repo_root
        )
        task.title = updated.title
        task.description = updated.description
        task.integration = updated.integration
        for tag in updated.tags:
            if tag not in task.tags:
                task.tags.append(tag)

    return sync_items_to_tasks(
        changes,
        task_repo=task_repo,
        item_key=lambda c: c.change_id,
        build_task=lambda c: generate_edison_task_from_openspec_change(
            c, prefix=prefix, project_root=repo_root
        ),
        update_task=_update_task,
        is_managed_task=lambda t: t.id.startswith(f"{prefix}-"),
        task_key=lambda t: _extract_change_id(t.id, prefix),
        removed_tag="removed-from-openspec",
        create_qa=create_qa,
        qa_created_by="openspec-import",
        dry_run=dry_run,
        project_root=repo_root,
        updatable_states={"todo"},
    )


def _extract_change_id(task_id: str, prefix: str) -> str:
    if not task_id.startswith(f"{prefix}-"):
        return task_id
    return task_id[len(prefix) + 1 :]


__all__ = [
    "OpenSpecImportError",
    "OpenSpecSource",
    "OpenSpecChange",
    "SyncResult",
    "parse_openspec_source",
    "list_openspec_changes",
    "generate_edison_task_from_openspec_change",
    "sync_openspec_changes",
]
