from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.common import APIModel, IDModel, TimestampedModel


class ModelRunBase(APIModel):
    prompt_version_id: int
    model_id: str
    params: dict[str, Any]
    seed: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    token_in: int | None = None
    token_out: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    status: str = "pending"


class ModelRunCreate(ModelRunBase):
    pass


class ModelRunRead(ModelRunBase, IDModel, TimestampedModel):
    pass


class OutputBase(APIModel):
    model_run_id: int
    case_id: int
    raw_text: str
    content: dict[str, Any] | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    meta: dict[str, Any] | None = None


class OutputCreate(OutputBase):
    pass


class OutputRead(OutputBase, IDModel, TimestampedModel):
    pass


class JudgmentBase(APIModel):
    output_id: int
    judge_model_id: str
    mode: str
    scores: dict[str, Any]
    rationale: dict[str, Any]
    safety: dict[str, Any] | None = None
    winner_output_id: int | None = None


class JudgmentCreate(JudgmentBase):
    pass


class JudgmentRead(JudgmentBase, IDModel, TimestampedModel):
    pass
