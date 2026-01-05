"""Shared next-steps helpers for QA workflow CLIs.

This module centralizes stable, user-facing guidance so multiple commands
(`task claim`, `task new`, `qa new`) don't drift in output shape or wording.
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class QANextStepsPayload(TypedDict):
    qaId: str
    qaState: str
    qaPath: str
    qaCreated: bool
    nextSteps: List[str]


_QA_OPEN_INSTRUCTION = (
    "Open the QA brief and update it (commands/expected results/evidence links) "
    "before/while implementing."
)


def build_qa_next_steps_payload(
    *,
    qa_id: str,
    qa_state: str,
    qa_path: str,
    created: bool,
) -> QANextStepsPayload:
    return {
        "qaId": str(qa_id),
        "qaState": str(qa_state),
        "qaPath": str(qa_path),
        "qaCreated": bool(created),
        "nextSteps": [_QA_OPEN_INSTRUCTION],
    }


def format_qa_next_steps_text(payload: QANextStepsPayload) -> str:
    created_hint = "created" if payload["qaCreated"] else "exists"
    return (
        f"QA: {payload['qaId']} ({payload['qaState']}; {created_hint})\n"
        f"QA Path: @{payload['qaPath']}\n"
        f"Next: {payload['nextSteps'][0]}"
    )


__all__ = [
    "QANextStepsPayload",
    "build_qa_next_steps_payload",
    "format_qa_next_steps_text",
]

