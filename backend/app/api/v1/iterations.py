from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Experiment, Iteration
from app.schemas.iteration import IterationCreate, IterationRead

router = APIRouter(prefix="/iterations", tags=["iterations"])


@router.post("", response_model=IterationRead, status_code=status.HTTP_201_CREATED)
async def create_iteration(payload: IterationCreate, db: AsyncSession = Depends(get_db)) -> Iteration:
    experiment = await db.get(Experiment, payload.experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    iteration = Iteration(
        experiment_id=payload.experiment_id,
        number=payload.number,
        selected_prompt_version_id=payload.selected_prompt_version_id,
        metrics_json=payload.metrics or {},
        started_at=payload.started_at,
        finished_at=payload.finished_at,
    )
    db.add(iteration)
    await db.commit()
    await db.refresh(iteration)
    return iteration


@router.get("/{iteration_id}", response_model=IterationRead)
async def get_iteration(iteration_id: int, db: AsyncSession = Depends(get_db)) -> Iteration:
    iteration = await db.get(Iteration, iteration_id)
    if not iteration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Iteration not found")
    return iteration


@router.get("", response_model=list[IterationRead])
async def list_iterations(experiment_id: int | None = None, db: AsyncSession = Depends(get_db)) -> list[Iteration]:
    stmt = select(Iteration)
    if experiment_id is not None:
        stmt = stmt.where(Iteration.experiment_id == experiment_id)
    result = await db.execute(stmt.order_by(Iteration.number))
    return list(result.scalars())
