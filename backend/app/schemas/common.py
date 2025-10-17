from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampedModel(APIModel):
    created_at: datetime
    updated_at: datetime


class IDModel(APIModel):
    id: int


class Paginated(APIModel):
    items: list[Any]
    total: int
