from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Review, Suggestion
from app.schemas.iteration import ReviewCreate, ReviewRead
from app.schemas.prompt import SuggestionRead

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.get("/queue", response_model=list[SuggestionRead])
async def get_queue(db: AsyncSession = Depends(get_db)) -> list[Suggestion]:
    result = await db.execute(select(Suggestion).order_by(Suggestion.created_at.desc()))
    return list(result.scalars())


@router.post("/reviews", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreate, db: AsyncSession = Depends(get_db)) -> Review:
    suggestion = await db.get(Suggestion, payload.suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    review = Review(
        suggestion_id=payload.suggestion_id,
        output_id=payload.output_id,
        reviewer_id=payload.reviewer_id,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review
