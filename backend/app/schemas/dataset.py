from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import APIModel, IDModel, TimestampedModel


class DatasetBase(APIModel):
    project_id: int
    name: str
    kind: str
    meta: dict[str, Any] = Field(default_factory=dict, alias="meta_json")


class DatasetCreate(DatasetBase):
    pass


class DatasetRead(DatasetBase, IDModel, TimestampedModel):
    pass


class CaseBase(APIModel):
    dataset_id: int
    input: dict[str, Any] = Field(alias="input_json")
    expected: dict[str, Any] | None = Field(default=None, alias="expected_json")
    tags: list[str] = Field(default_factory=list)
    difficulty: int | None = None


class CaseCreate(CaseBase):
    pass


class CaseRead(CaseBase, IDModel, TimestampedModel):
    pass
