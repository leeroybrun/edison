from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.common import APIModel, IDModel, TimestampedModel


class JobBase(APIModel):
    type: str
    payload: dict[str, Any]
    status: str = "pending"
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempts: int = 0
    last_error: str | None = None
    worker_id: str | None = None


class JobCreate(JobBase):
    pass


class JobRead(JobBase, IDModel, TimestampedModel):
    pass
