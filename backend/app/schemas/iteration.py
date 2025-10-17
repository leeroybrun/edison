from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.common import APIModel, IDModel, TimestampedModel


class IterationBase(APIModel):
    experiment_id: int
    number: int
    selected_prompt_version_id: int | None = None
    metrics: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class IterationCreate(IterationBase):
    pass


class IterationRead(IterationBase, IDModel, TimestampedModel):
    pass


class ReviewBase(APIModel):
    suggestion_id: int
    output_id: int | None = None
    reviewer_id: str
    decision: str
    notes: str | None = None


class ReviewCreate(ReviewBase):
    pass


class ReviewRead(ReviewBase, IDModel, TimestampedModel):
    pass
