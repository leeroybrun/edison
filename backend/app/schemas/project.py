from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import APIModel, IDModel, TimestampedModel


class ProjectBase(APIModel):
    name: str
    slug: str
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict, alias="settings_json")


class ProjectCreate(ProjectBase):
    created_by: str


class ProjectRead(ProjectBase, IDModel, TimestampedModel):
    created_by: str
