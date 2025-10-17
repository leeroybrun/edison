from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import APIModel, IDModel, TimestampedModel


class ExperimentBase(APIModel):
    project_id: int
    name: str
    description: str | None = None
    goal_text: str
    rubric: dict[str, Any] = Field(alias="rubric_json")
    safety: dict[str, Any] | None = Field(default=None, alias="safety_json")
    selector: dict[str, Any] | None = Field(default=None, alias="selector_json")
    refiner: dict[str, Any] | None = Field(default=None, alias="refiner_json")
    max_iterations: int | None = None
    budget_tokens: int | None = None
    status: str = "idle"


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentRead(ExperimentBase, IDModel, TimestampedModel):
    pass
