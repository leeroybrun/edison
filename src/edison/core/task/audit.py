"""Task backlog audit utilities.

This module performs a deterministic audit of task markdown files under
`.project/tasks` to help detect:
- missing/implicit links between tasks (mentions without depends_on/related)
- file-touch overlap risks (same file targeted by multiple tasks)
- likely duplicate tasks (title/body similarity)

Design goals:
- No LLM required
- Deterministic, stable output
- Reusable by CLI and future plan validators
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from edison.core.config.domains.task import TaskConfig
from edison.core.task.similarity import _jaccard, _shingle_set, _tokens
from edison.core.utils.paths.management import get_management_paths
from edison.core.utils.text import has_frontmatter, parse_frontmatter

_FILES_SECTION_RE = re.compile(
    r"##\s+Files\s+to\s+Create/Modify\s*\n+```[^\n]*\n(?P<code>.*?)\n```",
    re.S,
)


def _extract_files_to_modify(markdown_body: str) -> set[str]:
    m = _FILES_SECTION_RE.search(markdown_body or "")
    if not m:
        return set()
    code = m.group("code") or ""
    out: set[str] = set()
    for line in code.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        # Skip glob-style patterns; they aren't actionable for edit-collision analysis.
        if any(ch in line for ch in ("*", "?", "[", "]")):
            continue
        out.add(line)
    return out


def _infer_wave(task_id: str, markdown_body: str) -> str | None:
    # Common pattern in Edison tasks:
    # - **Wave:** 2 (something)
    # For plan-mode tasks: "...-wave1-..." inside the ID.
    m = re.search(r"\*\*Wave:\*\*\s*([0-9]+(?:\.[0-9]+)?)", markdown_body or "")
    if m:
        return m.group(1)
    m = re.search(r"\bwave\s*([0-9]+)\b", task_id or "", flags=re.I)
    if m:
        return m.group(1)
    return None


def _transitive_dep_closure(tasks: list[TaskAuditTask]) -> dict[str, set[str]]:
    """Return transitive depends_on closure for each task id.

    Used to suppress overlap warnings when tasks are explicitly ordered and therefore
    not at risk of competing edits.
    """

    by_id: dict[str, TaskAuditTask] = {t.id: t for t in tasks}
    memo: dict[str, set[str]] = {}
    visiting: set[str] = set()

    def dfs(task_id: str) -> set[str]:
        if task_id in memo:
            return memo[task_id]
        if task_id in visiting:
            # Cycle: leave empty here; other validators should surface cycles explicitly.
            return set()

        visiting.add(task_id)
        out: set[str] = set()
        task = by_id.get(task_id)
        if task is not None:
            for dep in task.depends_on:
                if dep not in by_id:
                    continue
                out.add(dep)
                out.update(dfs(dep))
        visiting.remove(task_id)

        memo[task_id] = out
        return out

    for t in tasks:
        dfs(t.id)

    return memo


@dataclass(frozen=True)
class TaskAuditIssue:
    code: str
    severity: str  # info | warning | error
    message: str
    data: dict[str, Any]


@dataclass(frozen=True)
class TaskAuditDuplicate:
    a: str
    b: str
    score: float


@dataclass(frozen=True)
class TaskAuditTask:
    id: str
    title: str
    path: Path
    state: str
    tags: list[str]
    depends_on: list[str]
    blocks_tasks: list[str]
    related: list[str]
    wave: str | None
    markdown_body: str
    files_to_modify: list[str]


@dataclass(frozen=True)
class TaskAuditReport:
    tasks: list[TaskAuditTask]
    issues: list[TaskAuditIssue]
    duplicates: list[TaskAuditDuplicate]
    include_session_tasks: bool = False
    tasks_roots_scanned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        roots = list(self.tasks_roots_scanned)
        waves: dict[str, int] = {}
        tags: dict[str, int] = {}
        for t in self.tasks:
            waves[t.wave or "unassigned"] = waves.get(t.wave or "unassigned", 0) + 1
            for tag in t.tags:
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "taskCount": len(self.tasks),
            "includeSessionTasks": bool(self.include_session_tasks),
            "tasksRootsScanned": roots,
            "waves": waves,
            "tags": tags,
            "issues": [
                {"code": i.code, "severity": i.severity, "message": i.message, **i.data} for i in self.issues
            ],
            "duplicates": [
                {"a": d.a, "b": d.b, "score": round(float(d.score), 3)} for d in self.duplicates
            ],
        }


def _load_tasks_from_paths(paths: list[Path]) -> list[TaskAuditTask]:
    tasks: list[TaskAuditTask] = []
    for path in sorted(paths):
        if path.name == "TEMPLATE.md":
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if not has_frontmatter(raw):
            continue

        doc = parse_frontmatter(raw)
        fm = doc.frontmatter or {}
        task_id = str(fm.get("id") or path.stem)
        title = str(fm.get("title") or "")
        state = path.parent.name
        body = doc.content or ""

        tasks.append(
            TaskAuditTask(
                id=task_id,
                title=title,
                path=path,
                state=state,
                tags=list(fm.get("tags") or []),
                depends_on=list(fm.get("depends_on") or []),
                blocks_tasks=list(fm.get("blocks_tasks") or []),
                related=list(fm.get("related") or fm.get("related_tasks") or []),
                wave=_infer_wave(task_id, body),
                markdown_body=body,
                files_to_modify=sorted(_extract_files_to_modify(body)),
            )
        )
    return tasks


def audit_tasks(
    *,
    project_root: Path,
    tasks_root: Path | None = None,
    include_session_tasks: bool = False,
    threshold: float | None = None,
    top_k: int | None = None,
) -> TaskAuditReport:
    """Audit `.project/tasks` for overlaps and planning issues.

    Args:
        project_root: Repo root.
        tasks_root: Optional override for `.project/tasks`.
        include_session_tasks: Reserved for future use; currently audits only global tasks.
        threshold: Similarity threshold override (defaults to tasks config threshold).
        top_k: Max duplicates per task (defaults to tasks config topK).
    """
    cfg = TaskConfig(repo_root=project_root)
    root = (tasks_root or cfg.tasks_root()).resolve()

    roots_scanned: list[str] = [str(root)]

    paths: list[Path] = list(root.rglob("*.md"))
    if include_session_tasks:
        sessions_root = get_management_paths(project_root).get_sessions_root()
        roots_scanned.append(str(sessions_root))
        paths.extend(list(sessions_root.glob("*/*/tasks/*/*.md")))

    tasks = _load_tasks_from_paths(paths)
    by_id = {t.id: t for t in tasks}
    ids = set(by_id.keys())

    issues: list[TaskAuditIssue] = []

    # Duplicate IDs across roots are always suspicious (likely partial restores or manual edits).
    id_to_paths: dict[str, list[str]] = {}
    for t in tasks:
        id_to_paths.setdefault(t.id, []).append(str(t.path))
    for tid, tpaths in sorted(id_to_paths.items()):
        uniq = sorted(set(tpaths))
        if len(uniq) < 2:
            continue
        issues.append(
            TaskAuditIssue(
                code="duplicate_task_id",
                severity="warning",
                message="Multiple task files share the same task id; audit signals may be ambiguous.",
                data={"taskId": tid, "paths": uniq},
            )
        )

    # --- Mentions without explicit links (depends_on/related/blocks) ---
    for t in tasks:
        linked = set(t.depends_on) | set(t.blocks_tasks) | set(t.related)
        for other_id in sorted(ids):
            if other_id == t.id:
                continue
            # Only count explicit mentions to reduce false positives:
            # - `001-foo` (inline code)
            # - task 001-foo
            if f"`{other_id}`" not in t.markdown_body and not re.search(
                rf"(?i)\btask\s+{re.escape(other_id)}\b",
                t.markdown_body,
            ):
                continue
            if other_id in linked:
                continue
            issues.append(
                TaskAuditIssue(
                    code="implicit_reference",
                    severity="warning",
                    message="Task mentions another task but does not link it via depends_on/related/blocks_tasks.",
                    data={"taskId": t.id, "mentionedTaskId": other_id},
                )
            )

    # --- File overlap risks ---
    dep_closure = _transitive_dep_closure(tasks)
    file_to_tasks: dict[str, list[str]] = {}
    for t in tasks:
        for f in t.files_to_modify:
            file_to_tasks.setdefault(f, []).append(t.id)
    for f, task_ids in sorted(file_to_tasks.items()):
        uniq = sorted(set(task_ids))
        if len(uniq) < 2:
            continue

        unordered_pairs: list[tuple[str, str]] = []
        for i, task_a_id in enumerate(uniq):
            for task_b_id in uniq[i + 1 :]:
                if task_a_id in dep_closure.get(task_b_id, set()) or task_b_id in dep_closure.get(
                    task_a_id, set()
                ):
                    continue
                unordered_pairs.append((task_a_id, task_b_id))

        # If every overlap is explicitly ordered by depends_on, we don't treat it as
        # a competing-edit risk.
        if not unordered_pairs:
            continue

        issues.append(
            TaskAuditIssue(
                code="file_overlap",
                severity="warning",
                message="Multiple tasks declare the same file in 'Files to Create/Modify' without an ordering dependency (risk of competing edits).",
                data={
                    "path": f,
                    "taskIds": uniq,
                    "unorderedTaskPairs": [{"a": a, "b": b} for a, b in unordered_pairs],
                },
            )
        )

    # --- Likely duplicates (deterministic title/body similarity) ---
    min_score = float(cfg.similarity_threshold() if threshold is None else threshold)
    limit = int(cfg.similarity_top_k() if top_k is None else top_k)

    use_shingles = bool(cfg.similarity_use_shingles())
    shingle_size = int(cfg.similarity_shingle_size())
    title_weight = float(cfg.similarity_title_weight())
    body_weight = float(cfg.similarity_body_weight())

    prepped: dict[
        str,
        tuple[
            set[str],
            set[str],
            set[tuple[str, ...]],
            set[tuple[str, ...]],
        ],
    ] = {}
    for t in tasks:
        title_tokens = _tokens(t.title)
        body_tokens = _tokens(t.markdown_body)
        if use_shingles:
            title_sh = _shingle_set(t.title, k=shingle_size)
            body_sh = _shingle_set(t.markdown_body, k=shingle_size)
        else:
            title_sh = set()
            body_sh = set()
        prepped[t.id] = (title_tokens, body_tokens, title_sh, body_sh)

    duplicates: list[TaskAuditDuplicate] = []
    seen_pairs: set[tuple[str, str]] = set()
    for a in tasks:
        a_title, a_body, a_title_sh, a_body_sh = prepped[a.id]
        scored: list[TaskAuditDuplicate] = []
        for b in tasks:
            if b.id == a.id:
                continue
            pair = tuple(sorted((a.id, b.id)))
            if pair in seen_pairs:
                continue
            b_title, b_body, b_title_sh, b_body_sh = prepped[b.id]

            title_score = _jaccard(a_title, b_title)
            body_score = _jaccard(a_body, b_body)
            if use_shingles:
                title_score = max(title_score, _jaccard(a_title_sh, b_title_sh))
                body_score = max(body_score, _jaccard(a_body_sh, b_body_sh))

            weighted = (title_weight * title_score) + (body_weight * body_score)
            score = max(weighted, title_score, body_score)
            if score < min_score:
                continue
            scored.append(TaskAuditDuplicate(a=pair[0], b=pair[1], score=score))

        scored.sort(key=lambda d: d.score, reverse=True)
        for d in scored[: max(limit, 0)]:
            pair = (d.a, d.b)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            duplicates.append(d)

    duplicates.sort(key=lambda d: d.score, reverse=True)

    return TaskAuditReport(
        tasks=tasks,
        issues=issues,
        duplicates=duplicates,
        include_session_tasks=bool(include_session_tasks),
        tasks_roots_scanned=roots_scanned,
    )


__all__ = [
    "TaskAuditDuplicate",
    "TaskAuditIssue",
    "TaskAuditReport",
    "TaskAuditTask",
    "audit_tasks",
]
