from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import APIModel, IDModel, TimestampedModel


class PromptVersionBase(APIModel):
    experiment_id: int
    parent_id: int | None = None
    text: str
    system_text: str | None = None
    shots: list[dict[str, Any]] | None = Field(default=None, alias="shots_json")
    tools_schema: dict[str, Any] | None = Field(default=None, alias="tools_schema_json")
    changelog: str | None = None
    created_by: str | None = None
    is_production: bool = False


class PromptVersionCreate(PromptVersionBase):
    pass


class PromptVersionRead(PromptVersionBase, IDModel, TimestampedModel):
    pass


class SuggestionBase(APIModel):
    prompt_version_id: int
    source: str
    diff_unified: str
    note: str


class SuggestionCreate(SuggestionBase):
    pass


class SuggestionRead(SuggestionBase, IDModel, TimestampedModel):
    pass
