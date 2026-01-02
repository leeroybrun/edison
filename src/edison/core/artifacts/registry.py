"""Artifact registry (minimal).

This is the single place to add new artifact "types" (task/qa/plan/etc.) for
shared artifact workflows (required-fill detection, verify commands, post-create UX).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactType:
    id: str


TASK = ArtifactType("task")
QA = ArtifactType("qa")
PLAN = ArtifactType("plan")


def known_artifact_types() -> tuple[ArtifactType, ...]:
    return (TASK, QA, PLAN)


__all__ = ["ArtifactType", "TASK", "QA", "PLAN", "known_artifact_types"]

