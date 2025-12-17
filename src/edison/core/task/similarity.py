"""Task similarity / duplicate detection (deterministic, project-wide).

This module centralizes "similar task" detection so it can be reused by:
- `edison session next` follow-up suggestion dedupe hints
- `edison task similar` CLI (ad-hoc duplicate detection)

Design goals:
- Deterministic (no LLM required)
- Project-wide (global + session-scoped tasks)
- Config-driven thresholds/weights via TaskConfig
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Iterable, Tuple

from edison.core.config.domains.task import TaskConfig
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository
from edison.core.utils.paths import PathResolver
from edison.core.utils.text.core import _shingles, _tokenize


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a.union(b)
    if not union:
        return 0.0
    return len(a.intersection(b)) / len(union)


def _tokens(text: str) -> set[str]:
    return set(_tokenize(text or ""))


def _shingle_set(text: str, *, k: int) -> set[tuple[str, ...]]:
    toks = _tokenize(text or "")
    return set(_shingles(toks, k=k)) if toks else set()


def _task_text(task: Task) -> tuple[str, str]:
    title = (task.title or "").strip()
    body = (task.description or "").strip()
    return title, body


@dataclass(frozen=True)
class SimilarTaskMatch:
    task_id: str
    score: float
    title: str
    state: str
    session_id: Optional[str]
    path: Path
    title_score: float
    body_score: float

    def to_session_next_dict(self) -> dict[str, object]:
        return {"taskId": self.task_id, "score": round(self.score, 2)}


class TaskSimilarityIndex:
    """Precomputed, reusable similarity index for project tasks."""

    def __init__(
        self,
        *,
        project_root: Path,
        tasks: List[Task],
        shingle_size: int,
        title_weight: float,
        body_weight: float,
        use_shingles: bool,
    ) -> None:
        self.project_root = project_root
        self._tasks = tasks
        self._shingle_size = max(int(shingle_size), 1)
        self._title_weight = float(title_weight)
        self._body_weight = float(body_weight)
        self._use_shingles = bool(use_shingles)

        # Precompute representations once for multi-query use.
        # Store (task, title_tokens, body_tokens, title_shingles, body_shingles)
        prepped: list[tuple[Task, set[str], set[str], set[tuple[str, ...]], set[tuple[str, ...]]]] = []
        for t in tasks:
            title, body = _task_text(t)
            title_tokens = _tokens(title)
            body_tokens = _tokens(body)
            if self._use_shingles:
                title_sh = _shingle_set(title, k=self._shingle_size)
                body_sh = _shingle_set(body, k=self._shingle_size)
            else:
                title_sh = set()
                body_sh = set()
            prepped.append((t, title_tokens, body_tokens, title_sh, body_sh))
        self._prepped = prepped

    @classmethod
    def build(
        cls,
        *,
        project_root: Optional[Path] = None,
        states: Optional[Iterable[str]] = None,
    ) -> "TaskSimilarityIndex":
        root = Path(project_root).resolve() if project_root is not None else PathResolver.resolve_project_root()
        cfg = TaskConfig(repo_root=root)
        repo = TaskRepository(project_root=root)

        tasks = repo.find_all()
        if states is not None:
            allowed = {str(s) for s in states}
            tasks = [t for t in tasks if str(t.state) in allowed]

        return cls(
            project_root=root,
            tasks=tasks,
            shingle_size=cfg.similarity_shingle_size(),
            title_weight=cfg.similarity_title_weight(),
            body_weight=cfg.similarity_body_weight(),
            use_shingles=cfg.similarity_use_shingles(),
        )

    def search(
        self,
        query: str,
        *,
        threshold: Optional[float] = None,
        top_k: Optional[int] = None,
        exclude_task_ids: Optional[Iterable[str]] = None,
    ) -> List[SimilarTaskMatch]:
        cfg = TaskConfig(repo_root=self.project_root)
        min_score = float(cfg.similarity_threshold() if threshold is None else threshold)
        limit = int(cfg.similarity_top_k() if top_k is None else top_k)
        excludes = {str(tid) for tid in (exclude_task_ids or [])}

        q_tokens_title = _tokens(query)
        q_tokens_body = q_tokens_title  # query is usually title-like; reuse
        if self._use_shingles:
            q_title_sh = _shingle_set(query, k=self._shingle_size)
            q_body_sh = q_title_sh
        else:
            q_title_sh = set()
            q_body_sh = set()

        scored: list[SimilarTaskMatch] = []
        for task, title_tokens, body_tokens, title_sh, body_sh in self._prepped:
            if task.id in excludes:
                continue

            title_score = _jaccard(q_tokens_title, title_tokens)
            body_score = _jaccard(q_tokens_body, body_tokens)
            if self._use_shingles:
                title_score = max(title_score, _jaccard(q_title_sh, title_sh))
                body_score = max(body_score, _jaccard(q_body_sh, body_sh))

            weighted = (self._title_weight * title_score) + (self._body_weight * body_score)
            # Prefer recall for duplicate detection: either a strong title match OR
            # a strong body match should be enough to surface candidates.
            score = max(weighted, title_score, body_score)
            if score < min_score:
                continue

            try:
                path = TaskRepository(project_root=self.project_root).get_path(task.id)
            except Exception:
                path = Path(task.id)

            scored.append(
                SimilarTaskMatch(
                    task_id=task.id,
                    score=float(score),
                    title=task.title,
                    state=task.state,
                    session_id=task.session_id,
                    path=path,
                    title_score=float(title_score),
                    body_score=float(body_score),
                )
            )

        scored.sort(key=lambda m: (m.score, m.title_score, m.body_score), reverse=True)
        return scored[: max(limit, 0)]


def find_similar_tasks_for_query(
    query: str,
    *,
    project_root: Optional[Path] = None,
    threshold: Optional[float] = None,
    top_k: Optional[int] = None,
    states: Optional[Iterable[str]] = None,
) -> List[SimilarTaskMatch]:
    index = TaskSimilarityIndex.build(project_root=project_root, states=states)
    return index.search(query, threshold=threshold, top_k=top_k)


def find_similar_tasks_for_task(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    threshold: Optional[float] = None,
    top_k: Optional[int] = None,
    states: Optional[Iterable[str]] = None,
) -> List[SimilarTaskMatch]:
    root = Path(project_root).resolve() if project_root is not None else PathResolver.resolve_project_root()
    repo = TaskRepository(project_root=root)
    task = repo.get(task_id)
    if not task:
        raise ValueError(f"Task not found: {task_id}")
    title, body = _task_text(task)
    query = "\n".join([t for t in (title, body) if t]).strip()
    if not query:
        query = task.id

    index = TaskSimilarityIndex.build(project_root=root, states=states)
    return index.search(
        query,
        threshold=threshold,
        top_k=top_k,
        exclude_task_ids=[task.id],
    )


__all__ = [
    "SimilarTaskMatch",
    "TaskSimilarityIndex",
    "find_similar_tasks_for_query",
    "find_similar_tasks_for_task",
]
