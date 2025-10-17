from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Experiment, PromptVersion, Suggestion
from app.schemas.prompt import PromptVersionCreate, PromptVersionRead, SuggestionCreate, SuggestionRead

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED)
async def create_prompt_version(
    payload: PromptVersionCreate, db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    experiment = await db.get(Experiment, payload.experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    prompt = PromptVersion(
        experiment_id=payload.experiment_id,
        parent_id=payload.parent_id,
        text=payload.text,
        system_text=payload.system_text,
        shots_json=payload.shots or [],
        tools_schema_json=payload.tools_schema or {},
        changelog=payload.changelog,
        created_by=payload.created_by,
        is_production=payload.is_production,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.get("/{prompt_id}", response_model=PromptVersionRead)
async def get_prompt_version(prompt_id: int, db: AsyncSession = Depends(get_db)) -> PromptVersion:
    prompt = await db.get(PromptVersion, prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found")
    return prompt


@router.get("", response_model=list[PromptVersionRead])
async def list_prompt_versions(
    experiment_id: int | None = None, db: AsyncSession = Depends(get_db)
) -> list[PromptVersion]:
    stmt = select(PromptVersion)
    if experiment_id is not None:
        stmt = stmt.where(PromptVersion.experiment_id == experiment_id)
    result = await db.execute(stmt.order_by(PromptVersion.created_at.desc()))
    return list(result.scalars())


@router.post("/{prompt_id}/suggestions", response_model=SuggestionRead, status_code=status.HTTP_201_CREATED)
async def create_suggestion(prompt_id: int, payload: SuggestionCreate, db: AsyncSession = Depends(get_db)) -> Suggestion:
    prompt = await db.get(PromptVersion, prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found")

    suggestion = Suggestion(
        prompt_version_id=prompt_id,
        source=payload.source,
        diff_unified=payload.diff_unified,
        note=payload.note,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.get("/{prompt_id}/suggestions", response_model=list[SuggestionRead])
async def list_suggestions(prompt_id: int, db: AsyncSession = Depends(get_db)) -> list[Suggestion]:
    stmt = select(Suggestion).where(Suggestion.prompt_version_id == prompt_id).order_by(Suggestion.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars())
