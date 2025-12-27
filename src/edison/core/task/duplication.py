"""Task duplication checks (pre-create warnings/blocks).

This module provides a small, reusable entrypoint for checking potential
duplicate tasks before creating new tasks (including follow-ups).

It is intentionally grounded in the task corpus:
- Uses `edison.core.task.similarity` (deterministic) for scoring.
- Optionally uses configured memory providers as query expansions (via config),
  but always maps results back onto real tasks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from edison.core.config.domains.task import TaskConfig
from edison.core.task.similarity import SimilarTaskMatch, find_similar_tasks_for_query


@dataclass(frozen=True)
class DuplicateTaskError(Exception):
    message: str
    matches: list[SimilarTaskMatch]

    def __str__(self) -> str:  # pragma: no cover (trivial)
        return self.message


def _draft_query(title: str, description: str) -> str:
    parts = [str(title or "").strip(), str(description or "").strip()]
    return "\n".join([p for p in parts if p]).strip()


def find_duplicate_tasks_for_draft(
    *,
    title: str,
    description: str = "",
    project_root: Path,
    threshold: Optional[float] = None,
    top_k: Optional[int] = None,
    states: Optional[Iterable[str]] = None,
) -> list[SimilarTaskMatch]:
    query = _draft_query(title, description)
    if not query:
        return []
    return find_similar_tasks_for_query(
        query,
        project_root=project_root,
        threshold=threshold,
        top_k=top_k,
        states=states,
    )


def check_duplicates_or_raise(
    *,
    title: str,
    description: str,
    project_root: Path,
) -> list[SimilarTaskMatch]:
    """Check duplicates for a task draft, respecting config.

    Returns matches. Raises DuplicateTaskError when configured to block.
    """
    cfg = TaskConfig(repo_root=project_root)
    if not cfg.similarity_precreate_enabled():
        return []
    if cfg.similarity_precreate_action() == "none":
        return []

    matches = find_duplicate_tasks_for_draft(
        title=title,
        description=description,
        project_root=project_root,
        threshold=cfg.similarity_precreate_threshold(),
        top_k=cfg.similarity_precreate_top_k(),
        states=cfg.similarity_precreate_states(),
    )

    if not matches:
        return []

    if cfg.similarity_precreate_action() == "block":
        raise DuplicateTaskError(
            message=f"Refusing to create task: found {len(matches)} possible duplicate(s).",
            matches=matches,
        )

    return matches


__all__ = [
    "DuplicateTaskError",
    "check_duplicates_or_raise",
    "find_duplicate_tasks_for_draft",
]
